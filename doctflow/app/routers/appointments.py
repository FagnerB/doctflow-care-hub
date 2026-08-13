from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db_session, rate_limit_public, rate_limit_public_generous
from app.exceptions import NotFoundError
from app.models.appointment import Appointment
from app.models.doctor import Doctor
from app.schemas.appointment import AppointmentCreatePublic, AppointmentPublicStatusResponse, AppointmentRead

from app.services.appointment_service import appointment_service

logger = logging.getLogger(__name__)

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


@router.post("", response_model=AppointmentRead, status_code=201, dependencies=[Depends(rate_limit_public)])
async def create_appointment(
    payload: AppointmentCreatePublic,
    session: AsyncSession = Depends(get_db_session),
) -> AppointmentRead:
    """Agendamento público do paciente (sem login).

    Valida o slot, grava a consulta e dispara a confirmação por WhatsApp para o
    paciente e o aviso para o médico.
    """
    appointment = await appointment_service.create_public_appointment(session, payload)
    await session.commit()

    appointment = await _load_appointment(session, appointment.id)

    # A consulta já está gravada: uma falha no envio de WhatsApp não pode
    # derrubar a resposta ao paciente. Fica registrada em notification_logs.
    try:
        await appointment_service.send_confirmation_notifications(session, appointment)
        await session.commit()
    except Exception:
        await session.rollback()
        logger.exception("confirmation_notification_failed", extra={"appointment_id": appointment.id})
        appointment = await _load_appointment(session, appointment.id)

    return AppointmentRead.model_validate(appointment)


@router.get(
    "/{appointment_id}/status",
    response_model=AppointmentPublicStatusResponse,
    dependencies=[Depends(rate_limit_public_generous)],
)
async def get_public_status(
    appointment_id: str,
    session: AsyncSession = Depends(get_db_session),
) -> AppointmentPublicStatusResponse:
    """Status da consulta pelo link enviado ao paciente (id UUID funciona como token)."""
    appointment = await appointment_service.get_public_status(session, appointment_id)
    return AppointmentPublicStatusResponse(
        id=appointment.id,
        status=appointment.status,
        scheduled_at=appointment.scheduled_at,
        duration_minutes=appointment.duration_minutes,
        confirmation_sent_at=appointment.confirmation_sent_at,
        reminder_sent_at=appointment.reminder_sent_at,
        doctor_full_name=appointment.doctor.user.full_name,
        patient_name=appointment.patient.name,
        patient_phone=appointment.patient.phone,
    )


# O webhook de WhatsApp saiu deste router para app/routers/webhooks.py, onde
# passou a exigir assinatura/segredo. Na versão anterior qualquer pessoa podia
# cancelar a consulta de outra apenas enviando o telefone dela neste endpoint.
