"""GET /patients/{id} -- isolamento por médico (IDOR fix)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _outro_medico_com_paciente(session) -> tuple[Doctor, Patient]:
    """Segundo médico, com um paciente e consulta próprios (não o `doctor` da fixture)."""
    user = User(
        id="user-doctor-2",
        email="dr.souza@example.com",
        role=UserRole.doctor,
        full_name="Bruno Souza",
        phone="+5511977776666",
    )
    session.add(user)
    await session.flush()

    doctor_row = Doctor(
        id="doctor-2",
        user_id=user.id,
        slug="dr-souza",
        specialty="Dermatologia",
        config_json={
            "consultation_duration_minutes": 30,
            "advance_booking_days": 30,
            "auto_confirm": True,
            "cancellation_policy_hours": 24,
            "working_hours": {},
        },
    )
    session.add(doctor_row)

    patient = Patient(id="patient-do-outro", name="Paciente do Outro Médico", phone="+5511911112222")
    session.add(patient)
    await session.flush()

    session.add(
        Appointment(
            id="appointment-do-outro",
            doctor_id=doctor_row.id,
            patient_id=patient.id,
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
            duration_minutes=30,
            status=AppointmentStatus.confirmed,
        )
    )
    await session.commit()
    return doctor_row, patient


async def test_medico_nao_le_paciente_de_outro_medico(client, session, doctor, doctor_token) -> None:
    _, patient = await _outro_medico_com_paciente(session)

    response = await client.get(f"/api/patients/{patient.id}", headers=auth(doctor_token))
    assert response.status_code == 404


async def test_medico_le_proprio_paciente(client, session, doctor, doctor_token) -> None:
    patient = Patient(id="patient-do-doctor-1", name="Paciente Meu", phone="+5511900001111")
    session.add(patient)
    await session.flush()
    session.add(
        Appointment(
            id="appointment-meu",
            doctor_id=doctor.id,
            patient_id=patient.id,
            scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
            duration_minutes=30,
            status=AppointmentStatus.confirmed,
        )
    )
    await session.commit()

    response = await client.get(f"/api/patients/{patient.id}", headers=auth(doctor_token))
    assert response.status_code == 200
    assert response.json()["id"] == patient.id


async def test_get_patient_paciente_inexistente(client, doctor, doctor_token) -> None:
    response = await client.get("/api/patients/nao-existe", headers=auth(doctor_token))
    assert response.status_code == 404
