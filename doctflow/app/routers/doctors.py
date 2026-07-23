from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_doctor, get_current_user, get_db_session
from app.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, UserRole
from app.models.doctor import Doctor
from app.models.schedule import ScheduleException
from app.models.user import User
from app.schemas.appointment import AppointmentRead, AppointmentStatusUpdate
from app.schemas.doctor import DoctorPublic, DoctorRead, DoctorUpdate
from app.schemas.schedule import AvailabilityResponse, ScheduleExceptionCreate, ScheduleExceptionRead
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/doctors", tags=["doctors"])


async def _load_doctor(session: AsyncSession, doctor_id: str) -> Doctor:
    doctor = await session.scalar(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id))
    if doctor is None:
        raise NotFoundError("Médico não encontrado")
    return doctor


@router.get("/{slug}", response_model=DoctorPublic)
async def get_public_doctor(slug: str, session: AsyncSession = Depends(get_db_session)) -> DoctorPublic:
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


@router.get("/{slug}/availability", response_model=AvailabilityResponse)
async def get_availability(
    slug: str,
    date: date = Query(..., description="Data no formato YYYY-MM-DD"),
    session: AsyncSession = Depends(get_db_session),
) -> AvailabilityResponse:
    slots = await appointment_service.get_available_slots(session, slug, date)
    return AvailabilityResponse(doctor_slug=slug, date=date, slots=slots)


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


@router.post("/me/exceptions", response_model=ScheduleExceptionRead)
async def create_exception(
    payload: ScheduleExceptionCreate,
    current_doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_db_session),
) -> ScheduleExceptionRead:
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
