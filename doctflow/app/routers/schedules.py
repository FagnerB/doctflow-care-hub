from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db_session, rate_limit_public_generous
from app.schemas.schedule import AvailabilityResponse
from app.services.appointment_service import appointment_service

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.get("/availability", response_model=AvailabilityResponse, dependencies=[Depends(rate_limit_public_generous)])
async def preview_availability(
    doctor_slug: str = Query(...),
    date: date = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> AvailabilityResponse:
    """Alias de /doctors/{slug}/availability aceitando o slug por query string."""
    # get_doctor_by_slug já levanta 404 quando não encontra.
    doctor = await appointment_service.get_doctor_by_slug(session, doctor_slug)
    slots = await appointment_service.get_available_slots(session, doctor.slug, date)
    return AvailabilityResponse(doctor_slug=doctor.slug, date=date, slots=slots)
