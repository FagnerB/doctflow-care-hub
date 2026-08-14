from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_doctor, get_db_session
from app.exceptions import NotFoundError
from app.models.appointment import Appointment
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
    # Paciente é global (sem doctor_id ainda), então o vínculo com o médico
    # logado é verificado por ter pelo menos uma consulta com ele -- sem isso,
    # qualquer médico autenticado conseguia ler dado de paciente de outro.
    has_link = exists().where(
        Appointment.patient_id == Patient.id,
        Appointment.doctor_id == current_doctor.id,
    )
    patient = await session.scalar(select(Patient).where(Patient.id == patient_id, has_link))
    if patient is None:
        raise NotFoundError("Paciente não encontrado")
    return PatientRead.model_validate(patient)
