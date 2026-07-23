from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db_session, rate_limit_public
from app.exceptions import NotFoundError
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.schemas.appointment import AppointmentCreatePublic, AppointmentPublicStatusResponse, AppointmentRead, AppointmentWebhookPayload
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/appointments", tags=["appointments"])


async def _load_appointment(session: AsyncSession, appointment_id: str) -> Appointment:
    appointment = await session.scalar(
        select(Appointment)
        .options(selectinload(Appointment.patient), selectinload(Appointment.doctor).selectinload(Doctor.user))
        .where(Appointment.id == appointment_id)
    )
    if appointment is None:
        raise NotFoundError("Agendamento não encontrado")
    return appointment


@router.post("", response_model=AppointmentRead, dependencies=[Depends(rate_limit_public)])
async def create_appointment(payload: AppointmentCreatePublic, session: AsyncSession = Depends(get_db_session)) -> AppointmentRead:
    appointment = await appointment_service.create_public_appointment(session, payload)
    await session.commit()
    await session.refresh(appointment)
    appointment = await _load_appointment(session, appointment.id)
    await appointment_service.send_confirmation_notifications(session, appointment)
    await session.commit()
    return AppointmentRead.model_validate(appointment)


@router.get("/{appointment_id}/status", response_model=AppointmentPublicStatusResponse)
async def get_public_status(appointment_id: str, session: AsyncSession = Depends(get_db_session)) -> AppointmentPublicStatusResponse:
    appointment = await appointment_service.get_public_status(session, appointment_id)
    return AppointmentPublicStatusResponse.model_validate(appointment)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(payload: AppointmentWebhookPayload, session: AsyncSession = Depends(get_db_session)) -> dict[str, bool]:
    if "CANCELAR" not in payload.message.upper():
        return {"success": True}
    appointment = await appointment_service.cancel_by_phone(session, payload.from_phone)
    await appointment_service.send_cancellation_notification(session, appointment)
    await session.commit()
    return {"success": True}
