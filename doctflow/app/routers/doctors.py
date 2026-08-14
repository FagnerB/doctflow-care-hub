from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_doctor, get_current_user, get_db_session, rate_limit_public_generous
from app.exceptions import ConflictError, NotFoundError
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus
from app.models.doctor import Doctor
from app.models.schedule import ScheduleException
from app.models.user import User
from app.schemas.appointment import AppointmentCreateByDoctor, AppointmentRead, AppointmentStatusUpdate
from app.schemas.doctor import DoctorPublic, DoctorRead, DoctorUpdate
from app.schemas.schedule import (
    AvailabilityResponse,
    DoctorStatsResponse,
    ScheduleExceptionCreate,
    ScheduleExceptionRead,
)
from app.services.appointment_service import appointment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["doctors"])


async def _load_doctor(session: AsyncSession, doctor_id: str) -> Doctor:
    doctor = await session.scalar(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id))
    if doctor is None:
        raise NotFoundError("Médico não encontrado")
    return doctor


# ATENÇÃO: as rotas /me* precisam ser declaradas ANTES de /{slug}. O FastAPI
# resolve na ordem de registro e /{slug} casaria com "me", devolvendo 404.


@router.get("/me", response_model=DoctorRead)
async def get_my_profile(current_doctor: Doctor = Depends(get_current_doctor), session: AsyncSession = Depends(get_db_session)) -> DoctorRead:
    doctor = await _load_doctor(session, current_doctor.id)
    return DoctorRead.model_validate(doctor)


@router.put("/me", response_model=DoctorRead)
async def update_my_profile(
    payload: DoctorUpdate,
    current_doctor: Doctor = Depends(get_current_doctor),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> DoctorRead:
    doctor = await _load_doctor(session, current_doctor.id)
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.specialty is not None:
        doctor.specialty = payload.specialty
    if payload.bio is not None:
        doctor.bio = payload.bio
    if payload.avatar_url is not None:
        doctor.avatar_url = payload.avatar_url
    if payload.config_json is not None:
        doctor.config_json = payload.config_json.model_dump(mode="json")
    await session.commit()
    refreshed = await _load_doctor(session, doctor.id)
    return DoctorRead.model_validate(refreshed)


@router.get("/me/stats", response_model=DoctorStatsResponse)
async def get_my_stats(
    reference_month: date | None = Query(default=None, description="Qualquer dia do mês desejado; padrão = mês atual"),
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> DoctorStatsResponse:
    """Relatório simples do dashboard: volume do mês, comparecimento e próximas consultas."""
    return await appointment_service.get_doctor_stats(session, current_doctor.id, reference_month)


@router.get("/me/appointments", response_model=list[AppointmentRead])
async def list_my_appointments(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: AppointmentStatus | None = Query(default=None),
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> list[AppointmentRead]:
    items = await appointment_service.list_doctor_appointments(session, current_doctor.id, date_from=date_from, date_to=date_to, status=status)
    return [AppointmentRead.model_validate(appointment) for appointment in items]


@router.post("/me/appointments", response_model=AppointmentRead, status_code=201)
async def create_my_appointment(
    payload: AppointmentCreateByDoctor,
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> AppointmentRead:
    """Agendamento manual pelo médico — telefone, balcão, encaixe fora do expediente.

    O paciente é criado automaticamente se o telefone informado não existir
    ainda (mesma lógica do agendamento público). Dispara a mesma notificação
    de confirmação do fluxo público por padrão — a menos que
    `notify_patient=False` (importação de agenda já existente, onde disparar
    confirmação retroativa para pacientes reais não faz sentido).
    """
    appointment = await appointment_service.create_doctor_appointment(session, current_doctor, payload)
    await session.commit()

    appointment = await session.scalar(
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.doctor).selectinload(Doctor.user))
        .where(Appointment.id == appointment.id)
    )

    if payload.notify_patient:
        try:
            await appointment_service.send_confirmation_notifications(session, appointment)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("confirmation_notification_failed", extra={"appointment_id": appointment.id})
            appointment = await session.scalar(
                select(Appointment).options(selectinload(Appointment.patient)).where(Appointment.id == appointment.id)
            )

    return AppointmentRead.model_validate(appointment)


@router.put("/me/appointments/{appointment_id}/status", response_model=AppointmentRead)
async def update_appointment_status(
    appointment_id: str,
    payload: AppointmentStatusUpdate,
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> AppointmentRead:
    appointment = await session.scalar(select(Appointment).options(selectinload(Appointment.patient)).where(Appointment.id == appointment_id, Appointment.doctor_id == current_doctor.id))
    if appointment is None:
        raise NotFoundError("Agendamento não encontrado")
    appointment.status = payload.status
    if payload.notes is not None:
        appointment.notes = payload.notes
    await session.commit()
    refreshed = await session.scalar(select(Appointment).options(selectinload(Appointment.patient)).where(Appointment.id == appointment_id))
    return AppointmentRead.model_validate(refreshed)


@router.post("/me/exceptions", response_model=ScheduleExceptionRead, status_code=201)
async def create_exception(
    payload: ScheduleExceptionCreate,
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> ScheduleExceptionRead:
    """Bloqueia um dia inteiro (sem horários) ou uma faixa (start_time/end_time).

    Recusa o bloqueio se já houver consultas ativas dentro da janela: o médico
    precisa remarcar/cancelar essas consultas antes, para não deixar paciente
    com consulta "fantasma" num horário que sumiu da agenda.
    """
    conflitos = await appointment_service.appointments_in_exception_window(
        session,
        doctor_id=current_doctor.id,
        exception_date=payload.exception_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    if conflitos:
        raise ConflictError(
            f"Existem {len(conflitos)} consulta(s) ativa(s) nesse período. "
            "Cancele ou remarque antes de bloquear."
        )

    exception = ScheduleException(
        doctor_id=current_doctor.id,
        exception_date=payload.exception_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason,
    )
    session.add(exception)
    await session.commit()
    await session.refresh(exception)
    return ScheduleExceptionRead.model_validate(exception)


@router.get("/me/exceptions", response_model=list[ScheduleExceptionRead])
async def list_exceptions(
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> list[ScheduleExceptionRead]:
    result = await session.scalars(select(ScheduleException).where(ScheduleException.doctor_id == current_doctor.id).order_by(ScheduleException.exception_date.desc()))
    return [ScheduleExceptionRead.model_validate(item) for item in result.all()]


@router.delete("/me/exceptions/{exception_id}")
async def delete_exception(
    exception_id: str,
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    exception = await session.get(ScheduleException, exception_id)
    if exception is None or exception.doctor_id != current_doctor.id:
        raise NotFoundError("Bloqueio não encontrado")
    await session.delete(exception)
    await session.commit()
    return {"success": True}


# --------------------------------------------------------------------------
# Rotas públicas por slug — sempre no fim do arquivo (ver aviso no topo).
# --------------------------------------------------------------------------


@router.get("/{slug}", response_model=DoctorPublic, dependencies=[Depends(rate_limit_public_generous)])
async def get_public_doctor(slug: str, session: AsyncSession = Depends(get_db_session)) -> DoctorPublic:
    """Perfil público do médico, usado na página /d/{slug}."""
    doctor = await session.scalar(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.slug == slug))
    if doctor is None:
        raise NotFoundError("Médico não encontrado")
    return DoctorPublic.model_validate(
        {
            "slug": doctor.slug,
            "full_name": doctor.user.full_name,
            "specialty": doctor.specialty,
            "bio": doctor.bio,
            "avatar_url": doctor.avatar_url,
            "is_verified": doctor.is_verified,
            "config_json": doctor.config_json,
        }
    )


@router.get("/{slug}/availability", response_model=AvailabilityResponse, dependencies=[Depends(rate_limit_public_generous)])
async def get_availability(
    slug: str,
    date: date = Query(..., description="Data no formato YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db_session),
) -> AvailabilityResponse:
    """Slots livres do médico na data — já descontando bloqueios e consultas."""
    slots = await appointment_service.get_available_slots(session, slug, date)
    return AvailabilityResponse(doctor_slug=slug, date=date, slots=slots)
