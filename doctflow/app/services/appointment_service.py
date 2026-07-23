from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.exceptions import ConflictError, NotFoundError, ForbiddenError
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, NotificationStatus, NotificationType, UserRole, normalize_br_phone
from app.models.doctor import Doctor
from app.models.notification_log import NotificationLog
from app.models.patient import Patient
from app.models.schedule import ScheduleException
from app.schemas.appointment import AppointmentCreatePublic, AppointmentStatusUpdate
from app.schemas.doctor import DoctorConfig
from app.schemas.patient import PatientCreate
from app.services.notification_service import NotificationService
from app.services.schedule_service import desired_datetime_to_local, desired_datetime_to_utc, fetch_doctor_schedule_context, generate_available_slots, validate_booking_window


CANCELLED_STATUSES = {
    AppointmentStatus.cancelled_by_patient,
    AppointmentStatus.cancelled_by_doctor,
}


class AppointmentService:
    def __init__(self) -> None:
        self.notifications = NotificationService()

    async def get_doctor_by_slug(self, session: AsyncSession, slug: str) -> Doctor:
        doctor = await session.scalar(select(Doctor).where(Doctor.slug == slug))
        if doctor is None:
            raise NotFoundError("Médico não encontrado")
        return doctor

    async def get_patient_by_phone(self, session: AsyncSession, phone: str) -> Patient | None:
        normalized = normalize_br_phone(phone)
        return await session.scalar(select(Patient).where(Patient.phone == normalized))

    async def get_or_create_patient(self, session: AsyncSession, payload: PatientCreate) -> Patient:
        existing = await self.get_patient_by_phone(session, payload.phone)
        if existing is not None:
            existing.name = payload.name
            existing.email = payload.email
            existing.cpf = payload.cpf
            await session.flush()
            return existing

        patient = Patient(name=payload.name, phone=payload.phone, email=str(payload.email) if payload.email else None, cpf=payload.cpf)
        session.add(patient)
        await session.flush()
        return patient

    async def get_available_slots(self, session: AsyncSession, doctor_slug: str, target_date: date):
        doctor = await self.get_doctor_by_slug(session, doctor_slug)
        _, appointments, exceptions = await fetch_doctor_schedule_context(session, doctor.id, target_date)
        return generate_available_slots(doctor, target_date, appointments, exceptions)

    async def create_public_appointment(self, session: AsyncSession, payload: AppointmentCreatePublic) -> Appointment:
        doctor = await self.get_doctor_by_slug(session, payload.doctor_slug)
        desired_datetime = desired_datetime_to_local(payload.desired_datetime)
        desired_datetime_utc = desired_datetime_to_utc(payload.desired_datetime)
        validate_booking_window(doctor, desired_datetime)

        doctor_config = DoctorConfig.model_validate(doctor.config_json or {})
        existing = await session.scalar(
            select(Appointment).where(
                Appointment.doctor_id == doctor.id,
                Appointment.scheduled_at == desired_datetime_utc,
                Appointment.status.notin_(CANCELLED_STATUSES),
            )
        )
        if existing is not None:
            raise ConflictError("Horário indisponível")

        _, appointments, exceptions = await fetch_doctor_schedule_context(session, doctor.id, desired_datetime.date())
        available_slots = generate_available_slots(doctor, desired_datetime.date(), appointments, exceptions, now=datetime.now(desired_datetime.tzinfo))
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
        await session.flush()

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
        query = select(Appointment).where(Appointment.doctor_id == doctor_id)
        if date_from is not None:
            query = query.where(Appointment.scheduled_at >= datetime.combine(date_from, time.min, tzinfo=ZoneInfo(settings.timezone)))
        if date_to is not None:
            query = query.where(Appointment.scheduled_at < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=ZoneInfo(settings.timezone)))
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

    async def cancel_by_phone(self, session: AsyncSession, phone: str) -> Appointment:
        patient = await self.get_patient_by_phone(session, phone)
        if patient is None:
            raise NotFoundError("Paciente não encontrado")
        now = datetime.now(timezone.utc)
        appointment = await session.scalar(
            select(Appointment)
            .where(
                Appointment.patient_id == patient.id,
                Appointment.status.notin_(CANCELLED_STATUSES),
                Appointment.scheduled_at >= now,
            )
            .order_by(Appointment.scheduled_at.asc())
        )
        if appointment is None:
            raise NotFoundError("Nenhuma consulta futura encontrada para cancelamento")
        appointment.status = AppointmentStatus.cancelled_by_patient
        await session.flush()
        return appointment

    async def send_confirmation_notifications(self, session: AsyncSession, appointment: Appointment) -> None:
        doctor = await session.scalar(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == appointment.doctor_id))
        patient = await session.get(Patient, appointment.patient_id)
        if doctor is None or patient is None:
            raise NotFoundError("Dados do agendamento incompletos")

        patient_message = self.notifications.build_confirmation_message(patient.name, doctor.user.full_name, appointment.scheduled_at)
        doctor_message = self.notifications.build_doctor_booking_message(patient.name, appointment.scheduled_at)

        patient_result = await self.notifications.send_whatsapp(patient.phone, patient_message)
        doctor_result = await self.notifications.send_whatsapp(doctor.user.phone, doctor_message)

        if patient_result.ok:
            appointment.confirmation_sent_at = datetime.now(timezone.utc)
            session.add(
                NotificationLog(
                    appointment_id=appointment.id,
                    type=NotificationType.confirmation,
                    status=NotificationStatus.sent,
                )
            )
        else:
            session.add(
                NotificationLog(
                    appointment_id=appointment.id,
                    type=NotificationType.confirmation,
                    status=NotificationStatus.failed,
                    error_message=patient_result.error_message,
                )
            )

        if not doctor_result.ok:
            session.add(
                NotificationLog(
                    appointment_id=appointment.id,
                    type=NotificationType.confirmation,
                    status=NotificationStatus.failed,
                    error_message=doctor_result.error_message,
                )
            )

        await session.flush()

    async def send_cancellation_notification(self, session: AsyncSession, appointment: Appointment) -> None:
        doctor = await session.scalar(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == appointment.doctor_id))
        patient = await session.get(Patient, appointment.patient_id)
        if doctor is None or patient is None:
            return
        message = self.notifications.build_cancellation_message(patient.name, appointment.scheduled_at)
        result = await self.notifications.send_whatsapp(patient.phone, message)
        session.add(
            NotificationLog(
                appointment_id=appointment.id,
                type=NotificationType.cancellation,
                status=NotificationStatus.sent if result.ok else NotificationStatus.failed,
                error_message=result.error_message,
            )
        )
        await session.flush()

    async def run_reminders(self, session: AsyncSession) -> tuple[int, int]:
        now = datetime.now(timezone.utc)
        sent = 0
        failed = 0
        for hours_ahead, notification_type in ((24, NotificationType.reminder_24h), (2, NotificationType.reminder_2h)):
            target_start = now + timedelta(hours=hours_ahead)
            target_end = target_start + timedelta(minutes=15)
            result = await session.scalars(
                select(Appointment).where(
                    Appointment.status == AppointmentStatus.confirmed,
                    Appointment.scheduled_at >= target_start,
                    Appointment.scheduled_at <= target_end,
                )
            )
            appointments = list(result.all())
            for appointment in appointments:
                existing_log = await session.scalar(
                    select(NotificationLog).where(
                        NotificationLog.appointment_id == appointment.id,
                        NotificationLog.type == notification_type,
                        NotificationLog.status == NotificationStatus.sent,
                    )
                )
                if existing_log is not None:
                    continue
                doctor = await session.get(Doctor, appointment.doctor_id)
                patient = await session.get(Patient, appointment.patient_id)
                if doctor is None or patient is None:
                    failed += 1
                    continue
                message = self.notifications.build_reminder_message(patient.name, doctor.user.full_name, appointment.scheduled_at, hours_ahead)
                delivery = await self.notifications.send_whatsapp(patient.phone, message)
                session.add(
                    NotificationLog(
                        appointment_id=appointment.id,
                        type=notification_type,
                        status=NotificationStatus.sent if delivery.ok else NotificationStatus.failed,
                        error_message=delivery.error_message,
                    )
                )
                if delivery.ok:
                    appointment.reminder_sent_at = datetime.now(timezone.utc)
                    sent += 1
                else:
                    failed += 1
            await session.flush()
        return sent, failed


appointment_service = AppointmentService()
