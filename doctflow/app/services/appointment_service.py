from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, NotificationStatus, NotificationType, normalize_br_phone
from app.models.doctor import Doctor
from app.models.notification_log import NotificationLog
from app.models.patient import Patient
from app.schemas.appointment import AppointmentCreatePublic, AppointmentStatusUpdate
from app.schemas.doctor import DoctorConfig
from app.schemas.patient import PatientCreate
from app.schemas.schedule import DoctorStatsResponse, UpcomingAppointmentSummary
from app.services.notification_service import NotificationService
from app.services.schedule_service import (
    desired_datetime_to_local,
    desired_datetime_to_utc,
    fetch_doctor_schedule_context,
    generate_available_slots,
    validate_booking_window,
)

logger = logging.getLogger(__name__)

CANCELLED_STATUSES = {
    AppointmentStatus.cancelled_by_patient,
    AppointmentStatus.cancelled_by_doctor,
}

# Status que ainda ocupam um horário na agenda.
ACTIVE_STATUSES = {
    AppointmentStatus.pending,
    AppointmentStatus.confirmed,
}


class AppointmentService:
    def __init__(self) -> None:
        self.notifications = NotificationService()

    # ------------------------------------------------------------------
    # Consultas auxiliares
    # ------------------------------------------------------------------

    async def get_doctor_by_slug(self, session: AsyncSession, slug: str) -> Doctor:
        doctor = await session.scalar(select(Doctor).where(Doctor.slug == slug))
        if doctor is None:
            raise NotFoundError("Médico não encontrado")
        return doctor

    async def _load_doctor_with_user(self, session: AsyncSession, doctor_id: str) -> Doctor | None:
        # Sempre com selectinload: em sessão async, acessar doctor.user de forma
        # lazy levanta MissingGreenlet.
        return await session.scalar(
            select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id)
        )

    async def get_patient_by_phone(self, session: AsyncSession, phone: str) -> Patient | None:
        normalized = normalize_br_phone(phone)
        return await session.scalar(select(Patient).where(Patient.phone == normalized))

    async def get_or_create_patient(self, session: AsyncSession, payload: PatientCreate) -> Patient:
        existing = await self.get_patient_by_phone(session, payload.phone)
        if existing is not None:
            existing.name = payload.name
            # Só sobrescreve dados opcionais quando vieram preenchidos, para não
            # apagar e-mail/CPF já cadastrados num agendamento anterior.
            if payload.email:
                existing.email = str(payload.email)
            if payload.cpf:
                existing.cpf = payload.cpf
            await session.flush()
            return existing

        patient = Patient(
            name=payload.name,
            phone=payload.phone,
            email=str(payload.email) if payload.email else None,
            cpf=payload.cpf,
        )
        session.add(patient)
        await session.flush()
        return patient

    async def get_available_slots(self, session: AsyncSession, doctor_slug: str, target_date: date):
        doctor = await self.get_doctor_by_slug(session, doctor_slug)
        _, appointments, exceptions = await fetch_doctor_schedule_context(session, doctor.id, target_date)
        return generate_available_slots(doctor, target_date, appointments, exceptions)

    # ------------------------------------------------------------------
    # Agendamento
    # ------------------------------------------------------------------

    async def create_public_appointment(self, session: AsyncSession, payload: AppointmentCreatePublic) -> Appointment:
        doctor = await self.get_doctor_by_slug(session, payload.doctor_slug)
        desired_datetime = desired_datetime_to_local(payload.desired_datetime)
        desired_datetime_utc = desired_datetime_to_utc(payload.desired_datetime)
        validate_booking_window(doctor, desired_datetime)

        doctor_config = DoctorConfig.model_validate(doctor.config_json or {})

        _, appointments, exceptions = await fetch_doctor_schedule_context(session, doctor.id, desired_datetime.date())
        available_slots = generate_available_slots(doctor, desired_datetime.date(), appointments, exceptions)
        if not any(slot.start_time == desired_datetime for slot in available_slots):
            raise ConflictError("Horário indisponível")

        patient = await self.get_or_create_patient(
            session,
            PatientCreate(
                name=payload.patient_name,
                phone=payload.patient_phone,
                email=payload.patient_email,
                cpf=payload.patient_cpf,
            ),
        )

        appointment = Appointment(
            doctor_id=doctor.id,
            patient_id=patient.id,
            scheduled_at=desired_datetime_utc,
            duration_minutes=doctor_config.consultation_duration_minutes,
            status=AppointmentStatus.confirmed if doctor_config.auto_confirm else AppointmentStatus.pending,
            notes=payload.notes,
        )
        session.add(appointment)
        try:
            await session.flush()
        except IntegrityError as exc:
            # O índice único parcial (doctor_id, scheduled_at) é a defesa real
            # contra dois pacientes agendando o mesmo horário simultaneamente:
            # a checagem de slots acima sofre corrida entre requisições.
            await session.rollback()
            raise ConflictError("Horário indisponível") from exc

        return appointment

    async def update_status(self, session: AsyncSession, appointment_id: str, status_update: AppointmentStatusUpdate) -> Appointment:
        appointment = await session.get(Appointment, appointment_id)
        if appointment is None:
            raise NotFoundError("Agendamento não encontrado")
        appointment.status = status_update.status
        if status_update.notes:
            appointment.notes = status_update.notes
        await session.flush()
        return appointment

    async def list_doctor_appointments(
        self,
        session: AsyncSession,
        doctor_id: str,
        date_from: date | None = None,
        date_to: date | None = None,
        status: AppointmentStatus | None = None,
    ) -> list[Appointment]:
        local_tz = ZoneInfo(settings.timezone)
        query = select(Appointment).where(Appointment.doctor_id == doctor_id)
        if date_from is not None:
            query = query.where(Appointment.scheduled_at >= datetime.combine(date_from, time.min, tzinfo=local_tz))
        if date_to is not None:
            query = query.where(
                Appointment.scheduled_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=local_tz)
            )
        if status is not None:
            query = query.where(Appointment.status == status)
        query = query.options(selectinload(Appointment.patient))
        result = await session.scalars(query.order_by(Appointment.scheduled_at.asc()))
        return list(result.all())

    async def get_public_status(self, session: AsyncSession, appointment_id: str):
        appointment = await session.get(Appointment, appointment_id)
        if appointment is None:
            raise NotFoundError("Agendamento não encontrado")
        return appointment

    # ------------------------------------------------------------------
    # Bloqueios de agenda
    # ------------------------------------------------------------------

    async def appointments_in_exception_window(
        self,
        session: AsyncSession,
        *,
        doctor_id: str,
        exception_date: date,
        start_time: time | None,
        end_time: time | None,
    ) -> list[Appointment]:
        """Consultas ativas que cairiam dentro do bloqueio pretendido."""
        local_tz = ZoneInfo(settings.timezone)
        if start_time is None or end_time is None:
            window_start = datetime.combine(exception_date, time.min, tzinfo=local_tz)
            window_end = datetime.combine(exception_date + timedelta(days=1), time.min, tzinfo=local_tz)
        else:
            window_start = datetime.combine(exception_date, start_time, tzinfo=local_tz)
            window_end = datetime.combine(exception_date, end_time, tzinfo=local_tz)

        result = await session.scalars(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(ACTIVE_STATUSES),
                Appointment.scheduled_at >= window_start,
                Appointment.scheduled_at < window_end,
            )
        )
        return list(result.all())

    # ------------------------------------------------------------------
    # Cancelamento
    # ------------------------------------------------------------------

    def _cancellation_deadline_ok(self, doctor: Doctor, appointment: Appointment) -> bool:
        """Verifica a política `cancellation_policy_hours` do médico."""
        config = DoctorConfig.model_validate(doctor.config_json or {})
        if config.cancellation_policy_hours <= 0:
            return True
        scheduled_at = appointment.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        limite = scheduled_at - timedelta(hours=config.cancellation_policy_hours)
        return datetime.now(timezone.utc) <= limite

    async def cancel_by_phone(self, session: AsyncSession, phone: str) -> Appointment:
        """Cancela a próxima consulta ativa do paciente identificado pelo telefone."""
        patient = await self.get_patient_by_phone(session, phone)
        if patient is None:
            raise NotFoundError("Paciente não encontrado")

        now = datetime.now(timezone.utc)
        appointment = await session.scalar(
            select(Appointment)
            .where(
                Appointment.patient_id == patient.id,
                Appointment.status.in_(ACTIVE_STATUSES),
                Appointment.scheduled_at >= now,
            )
            .order_by(Appointment.scheduled_at.asc())
        )
        if appointment is None:
            raise NotFoundError("Nenhuma consulta futura encontrada para cancelamento")

        doctor = await self._load_doctor_with_user(session, appointment.doctor_id)
        if doctor is None:
            raise NotFoundError("Médico do agendamento não encontrado")

        if not self._cancellation_deadline_ok(doctor, appointment):
            config = DoctorConfig.model_validate(doctor.config_json or {})
            raise ForbiddenError(
                f"O cancelamento pelo paciente só é permitido até {config.cancellation_policy_hours}h "
                "antes da consulta. Entre em contato com o consultório."
            )

        appointment.status = AppointmentStatus.cancelled_by_patient
        await session.flush()
        return appointment

    # ------------------------------------------------------------------
    # Notificações
    # ------------------------------------------------------------------

    def _log(
        self,
        session: AsyncSession,
        appointment_id: str,
        notification_type: NotificationType,
        ok: bool,
        error_message: str | None,
    ) -> None:
        session.add(
            NotificationLog(
                appointment_id=appointment_id,
                type=notification_type,
                status=NotificationStatus.sent if ok else NotificationStatus.failed,
                error_message=error_message,
            )
        )

    async def send_confirmation_notifications(self, session: AsyncSession, appointment: Appointment) -> None:
        """Confirma no WhatsApp do paciente e avisa o médico do novo agendamento."""
        doctor = await self._load_doctor_with_user(session, appointment.doctor_id)
        patient = await session.get(Patient, appointment.patient_id)
        if doctor is None or patient is None:
            raise NotFoundError("Dados do agendamento incompletos")

        patient_message = self.notifications.build_confirmation_message(
            patient.name, doctor.user.full_name, appointment.scheduled_at
        )
        doctor_message = self.notifications.build_doctor_booking_message(
            patient.name, patient.phone, appointment.scheduled_at
        )

        patient_result = await self.notifications.send_whatsapp(patient.phone, patient_message)
        doctor_result = await self.notifications.send_whatsapp(doctor.user.phone, doctor_message)

        if patient_result.ok:
            appointment.confirmation_sent_at = datetime.now(timezone.utc)
        self._log(session, appointment.id, NotificationType.confirmation, patient_result.ok, patient_result.error_message)

        if not doctor_result.ok:
            self._log(
                session,
                appointment.id,
                NotificationType.confirmation,
                False,
                f"Aviso ao médico falhou: {doctor_result.error_message}",
            )

        await session.flush()

    async def send_cancellation_notifications(self, session: AsyncSession, appointment: Appointment) -> None:
        """Envia recibo ao paciente e avisa o médico sobre o cancelamento."""
        doctor = await self._load_doctor_with_user(session, appointment.doctor_id)
        patient = await session.get(Patient, appointment.patient_id)
        if doctor is None or patient is None:
            return

        patient_result = await self.notifications.send_whatsapp(
            patient.phone,
            self.notifications.build_patient_cancellation_message(doctor.user.full_name, appointment.scheduled_at),
        )
        doctor_result = await self.notifications.send_whatsapp(
            doctor.user.phone,
            self.notifications.build_doctor_cancellation_message(patient.name, appointment.scheduled_at),
        )

        self._log(
            session,
            appointment.id,
            NotificationType.cancellation,
            patient_result.ok,
            patient_result.error_message,
        )
        if not doctor_result.ok:
            self._log(
                session,
                appointment.id,
                NotificationType.cancellation,
                False,
                f"Aviso ao médico falhou: {doctor_result.error_message}",
            )
        await session.flush()

    async def run_reminders(self, session: AsyncSession) -> tuple[int, int]:
        """Dispara lembretes de 24h e 2h.

        A janela de busca acompanha `reminders_window_minutes` para que nenhuma
        consulta caia entre duas execuções do scheduler. Repetições são evitadas
        pelo NotificationLog, então rodar o job com folga é seguro.
        """
        now = datetime.now(timezone.utc)
        window = timedelta(minutes=settings.reminders_window_minutes)
        sent = 0
        failed = 0

        for hours_ahead, notification_type in ((24, NotificationType.reminder_24h), (2, NotificationType.reminder_2h)):
            target_start = now + timedelta(hours=hours_ahead)
            target_end = target_start + window

            result = await session.scalars(
                select(Appointment)
                .options(
                    selectinload(Appointment.patient),
                    selectinload(Appointment.doctor).selectinload(Doctor.user),
                )
                .where(
                    Appointment.status == AppointmentStatus.confirmed,
                    Appointment.scheduled_at >= target_start,
                    Appointment.scheduled_at <= target_end,
                )
            )

            for appointment in result.all():
                already_sent = await session.scalar(
                    select(NotificationLog.id).where(
                        NotificationLog.appointment_id == appointment.id,
                        NotificationLog.type == notification_type,
                        NotificationLog.status == NotificationStatus.sent,
                    )
                )
                if already_sent is not None:
                    continue

                patient = appointment.patient
                doctor = appointment.doctor
                if patient is None or doctor is None or doctor.user is None:
                    logger.warning("reminder_skipped_incomplete", extra={"appointment_id": appointment.id})
                    failed += 1
                    continue

                message = self.notifications.build_reminder_message(
                    patient.name, doctor.user.full_name, appointment.scheduled_at, hours_ahead
                )
                delivery = await self.notifications.send_whatsapp(patient.phone, message)
                self._log(session, appointment.id, notification_type, delivery.ok, delivery.error_message)

                if delivery.ok:
                    appointment.reminder_sent_at = datetime.now(timezone.utc)
                    sent += 1
                else:
                    failed += 1

            await session.flush()

        return sent, failed

    # ------------------------------------------------------------------
    # Relatórios
    # ------------------------------------------------------------------

    async def get_doctor_stats(
        self,
        session: AsyncSession,
        doctor_id: str,
        reference_month: date | None = None,
    ) -> DoctorStatsResponse:
        """Agregados do mês + próximas consultas, para o dashboard do médico."""
        local_tz = ZoneInfo(settings.timezone)
        reference = reference_month or datetime.now(local_tz).date()
        month_start = datetime.combine(reference.replace(day=1), time.min, tzinfo=local_tz)
        if reference.month == 12:
            next_month_first = reference.replace(year=reference.year + 1, month=1, day=1)
        else:
            next_month_first = reference.replace(month=reference.month + 1, day=1)
        month_end = datetime.combine(next_month_first, time.min, tzinfo=local_tz)

        rows = await session.execute(
            select(Appointment.status, func.count(Appointment.id))
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.scheduled_at >= month_start,
                Appointment.scheduled_at < month_end,
            )
            .group_by(Appointment.status)
        )
        counts: dict[AppointmentStatus, int] = {status: total for status, total in rows.all()}

        completed = counts.get(AppointmentStatus.completed, 0)
        no_show = counts.get(AppointmentStatus.no_show, 0)
        cancelled = counts.get(AppointmentStatus.cancelled_by_patient, 0) + counts.get(
            AppointmentStatus.cancelled_by_doctor, 0
        )
        confirmed = counts.get(AppointmentStatus.confirmed, 0)
        total = sum(counts.values())

        # Taxa de comparecimento considera só consultas com desfecho conhecido.
        denominator = completed + no_show
        attendance_rate = round((completed / denominator) * 100, 2) if denominator else 0.0

        upcoming_result = await session.scalars(
            select(Appointment)
            .options(selectinload(Appointment.patient))
            .where(
                Appointment.doctor_id == doctor_id,
                Appointment.status.in_(ACTIVE_STATUSES),
                Appointment.scheduled_at >= datetime.now(timezone.utc),
            )
            .order_by(Appointment.scheduled_at.asc())
            .limit(10)
        )
        upcoming = [
            UpcomingAppointmentSummary(
                id=item.id,
                patient_name=item.patient.name if item.patient else "—",
                patient_phone=item.patient.phone if item.patient else "—",
                scheduled_at=item.scheduled_at,
                duration_minutes=item.duration_minutes,
                status=item.status.value,
            )
            for item in upcoming_result.all()
        ]

        return DoctorStatsResponse(
            month=reference.strftime("%Y-%m"),
            total_appointments=total,
            confirmed=confirmed,
            completed=completed,
            no_show=no_show,
            cancelled=cancelled,
            attendance_rate=attendance_rate,
            upcoming=upcoming,
        )


appointment_service = AppointmentService()
