from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_doctor, get_current_user, get_db_session, require_owner
from app.exceptions import NotFoundError
from app.models.patient import Patient
from app.models.user import User
from app.models.common import UserRole
from app.schemas.patient import PatientRead

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/{patient_id}", response_model=PatientRead)
async def get_patient(
    patient_id: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> PatientRead:
    if current_user.role not in {UserRole.owner, UserRole.doctor}:
        raise NotFoundError("Paciente não encontrado")
    patient = await session.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError("Paciente não encontrado")
    return PatientRead.model_validate(patient)
