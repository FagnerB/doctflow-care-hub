from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_doctor, get_db_session
from app.exceptions import NotFoundError
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.schemas.patient import PatientRead

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(
    patient_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_doctor: Doctor = Depends(get_current_doctor),
) -> PatientRead:
    patient = await session.scalar(
        select(Patient).where(Patient.id == patient_id, Patient.doctor_id == current_doctor.id)
    )
    if patient is None:
        raise NotFoundError("Paciente não encontrado")
    return PatientRead.model_validate(patient)
