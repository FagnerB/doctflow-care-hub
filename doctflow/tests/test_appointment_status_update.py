"""PUT /doctors/me/appointments/{id}/status -- P2, registrar comparecimento/falta.

Endpoint já existia (usado por "Confirmar"/"Concluída"/"Cancelar" no
dashboard) mas não tinha nenhum teste. Cobre os dois status novos no
dashboard (no_show, completed) e o isolamento entre médicos.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, UserRole, normalize_name
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from app.services.auth_service import auth_service


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _criar_consulta(session, doctor, *, appointment_id: str = "appt-status-1") -> Appointment:
    patient = Patient(
        doctor_id=doctor.id, name="Paciente Status", name_key=normalize_name("Paciente Status"), phone="+5511900001234"
    )
    session.add(patient)
    await session.flush()
    appointment = Appointment(
        id=appointment_id,
        doctor_id=doctor.id,
        patient_id=patient.id,
        scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
        duration_minutes=30,
        status=AppointmentStatus.confirmed,
    )
    session.add(appointment)
    await session.commit()
    return appointment


async def _segundo_medico(session) -> tuple[Doctor, str]:
    user = User(
        id="user-doctor-status-2",
        email="dr.status2@example.com",
        role=UserRole.doctor,
        full_name="Bruno Status",
        phone="+5511900002222",
    )
    session.add(user)
    await session.flush()
    doctor_row = Doctor(
        id="doctor-status-2",
        user_id=user.id,
        slug="dr-status-2",
        specialty="Pediatria",
        config_json={
            "consultation_duration_minutes": 30, "advance_booking_days": 30, "auto_confirm": True,
            "cancellation_policy_hours": 24, "working_hours": {},
        },
    )
    session.add(doctor_row)
    await session.commit()

    class _User:
        id = user.id
        role = UserRole.doctor

    token, _ = auth_service.create_access_token(_User())  # type: ignore[arg-type]
    return doctor_row, token


async def test_marca_consulta_como_nao_compareceu(client, session, doctor, doctor_token) -> None:
    appointment = await _criar_consulta(session, doctor)

    response = await client.put(
        f"/api/doctors/me/appointments/{appointment.id}/status",
        json={"status": "no_show"},
        headers=auth(doctor_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "no_show"

    await session.refresh(appointment)
    assert appointment.status == AppointmentStatus.no_show


async def test_marca_consulta_como_concluida(client, session, doctor, doctor_token) -> None:
    appointment = await _criar_consulta(session, doctor)

    response = await client.put(
        f"/api/doctors/me/appointments/{appointment.id}/status",
        json={"status": "completed"},
        headers=auth(doctor_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"


async def test_atualiza_status_com_observacao(client, session, doctor, doctor_token) -> None:
    appointment = await _criar_consulta(session, doctor)

    response = await client.put(
        f"/api/doctors/me/appointments/{appointment.id}/status",
        json={"status": "no_show", "notes": "Paciente avisou depois que esqueceu."},
        headers=auth(doctor_token),
    )
    assert response.status_code == 200
    assert response.json()["notes"] == "Paciente avisou depois que esqueceu."


async def test_medico_nao_atualiza_status_de_consulta_de_outro_medico(client, session, doctor, doctor_token) -> None:
    outro_doctor, _ = await _segundo_medico(session)
    appointment = await _criar_consulta(session, outro_doctor, appointment_id="appt-do-outro-medico")

    response = await client.put(
        f"/api/doctors/me/appointments/{appointment.id}/status",
        json={"status": "no_show"},
        headers=auth(doctor_token),
    )
    assert response.status_code == 404

    await session.refresh(appointment)
    assert appointment.status == AppointmentStatus.confirmed  # não mudou


async def test_atualizar_status_exige_autenticacao(client, session, doctor) -> None:
    appointment = await _criar_consulta(session, doctor)

    response = await client.put(
        f"/api/doctors/me/appointments/{appointment.id}/status",
        json={"status": "no_show"},
    )
    assert response.status_code == 401


async def test_atualizar_status_consulta_inexistente(client, doctor_token) -> None:
    response = await client.put(
        "/api/doctors/me/appointments/nao-existe/status",
        json={"status": "no_show"},
        headers=auth(doctor_token),
    )
    assert response.status_code == 404
