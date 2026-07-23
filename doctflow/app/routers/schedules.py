from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session
from app.exceptions import NotFoundError
from app.models.doctor import Doctor
from app.schemas.schedule import AvailabilityResponse
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/availability", response_model=AvailabilityResponse)
async def preview_availability(
    doctor_slug: str = Query(...),
    date: date = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> AvailabilityResponse:
    doctor = await appointment_service.get_doctor_by_slug(session, doctor_slug)
    slots = await appointment_service.get_available_slots(session, doctor.slug, date)
    if doctor is None:
        raise NotFoundError("Médico não encontrado")
    return AvailabilityResponse(doctor_slug=doctor.slug, date=date, slots=slots)
