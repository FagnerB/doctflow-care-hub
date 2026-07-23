from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db_session, require_owner
from app.exceptions import ConflictError
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, UserRole
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.appointment import ReminderRunResponse
from app.schemas.doctor import DoctorCreate, DoctorListResponse, DoctorRead
from app.services.appointment_service import appointment_service
from app.services.auth_service import auth_service

router = APIRouter(prefix="/admin", tags=["admin"])


async def _create_doctor_account(session: AsyncSession, payload: DoctorCreate) -> Doctor:
    if await session.scalar(select(User).where(User.email == payload.email)) is not None:
        raise ConflictError("Usuário já existe")
    if await session.scalar(select(User).where(User.phone == payload.phone)) is not None:
        raise ConflictError("Telefone já cadastrado")
    if await session.scalar(select(Doctor).where(Doctor.slug == payload.slug)) is not None:
        raise ConflictError("Slug já utilizado")

    supabase_user_id = await auth_service.create_supabase_user(payload.email, payload.full_name, payload.phone, UserRole.doctor)
    user = await auth_service.upsert_user_profile(
        session,
        user_id=supabase_user_id,
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        role=UserRole.doctor,
    )
    doctor = await auth_service.ensure_doctor_profile(
        session,
        user=user,
        slug=payload.slug,
        specialty=payload.specialty,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
        is_verified=payload.is_verified,
        config_json=payload.config_json.model_dump(mode="json"),
    )
    await session.commit()
    doctor = await session.scalar(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor.id))
    return doctor


@router.get("/doctors", response_model=DoctorListResponse)
async def list_doctors(
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_owner),
) -> DoctorListResponse:
    result = await session.scalars(select(Doctor).options(selectinload(Doctor.user)).order_by(Doctor.created_at.desc()))
    items = [DoctorRead.model_validate(doctor) for doctor in result.all()]
    return DoctorListResponse(items=items, total=len(items))


@router.post("/doctors", response_model=DoctorRead)
async def create_doctor(
    payload: DoctorCreate,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_owner),
) -> DoctorRead:
    doctor = await _create_doctor_account(session, payload)
    return DoctorRead.model_validate(doctor)


@router.get("/stats")
async def get_stats(
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_owner),
) -> dict[str, object]:
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    next_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc) if now.month == 12 else datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

    total_doctors = await session.scalar(select(func.count(Doctor.id))) or 0
    appointments_month = await session.scalar(
        select(func.count(Appointment.id)).where(Appointment.scheduled_at >= month_start, Appointment.scheduled_at < next_month)
    ) or 0
    attended = await session.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.scheduled_at >= month_start,
            Appointment.scheduled_at < next_month,
            Appointment.status == AppointmentStatus.completed,
        )
    ) or 0
    no_show = await session.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.scheduled_at >= month_start,
            Appointment.scheduled_at < next_month,
            Appointment.status == AppointmentStatus.no_show,
        )
    ) or 0
    denominator = attended + no_show
    attendance_rate = round((attended / denominator) * 100, 2) if denominator else 0.0
    return {
        "success": True,
        "total_doctors": total_doctors,
        "appointments_month": appointments_month,
        "attendance_rate": attendance_rate,
    }


@router.post("/reminders/run", response_model=ReminderRunResponse)
async def run_reminders(
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_owner),
) -> ReminderRunResponse:
    sent, failed = await appointment_service.run_reminders(session)
    await session.commit()
    return ReminderRunResponse(sent=sent, failed=failed)
