"""Relatório do dashboard do médico."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.appointment import Appointment
from app.models.common import AppointmentStatus
from app.models.patient import Patient


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _semear(session, doctor) -> None:
    patient = Patient(id="patient-stats", name="Carlos Souza", phone="+5511912345678")
    session.add(patient)
    await session.flush()

    agora = datetime.now(timezone.utc)
    registros = [
        ("a1", agora - timedelta(days=1), AppointmentStatus.completed),
        ("a2", agora - timedelta(days=2), AppointmentStatus.completed),
        ("a3", agora - timedelta(days=3), AppointmentStatus.no_show),
        ("a4", agora - timedelta(days=4), AppointmentStatus.cancelled_by_patient),
        ("a5", agora + timedelta(days=1), AppointmentStatus.confirmed),
    ]
    for appointment_id, quando, status in registros:
        session.add(
            Appointment(
                id=appointment_id,
                doctor_id=doctor.id,
                patient_id=patient.id,
                scheduled_at=quando,
                duration_minutes=30,
                status=status,
            )
        )
    await session.commit()


async def test_stats_agrega_o_mes_corrente(client, session, doctor, doctor_token) -> None:
    await _semear(session, doctor)

    response = await client.get("/api/doctors/me/stats", headers=auth(doctor_token))
    assert response.status_code == 200
    body = response.json()

    assert body["completed"] == 2
    assert body["no_show"] == 1
    assert body["cancelled"] == 1
    assert body["confirmed"] == 1
    # Taxa considera apenas desfechos conhecidos: 2 comparecimentos / 3.
    assert body["attendance_rate"] == 66.67


async def test_stats_lista_proximas_consultas(client, session, doctor, doctor_token) -> None:
    await _semear(session, doctor)

    body = (await client.get("/api/doctors/me/stats", headers=auth(doctor_token))).json()

    assert len(body["upcoming"]) == 1
    assert body["upcoming"][0]["patient_name"] == "Carlos Souza"
    assert body["upcoming"][0]["status"] == "confirmed"


async def test_stats_sem_dados_nao_divide_por_zero(client, doctor, doctor_token) -> None:
    body = (await client.get("/api/doctors/me/stats", headers=auth(doctor_token))).json()
    assert body["total_appointments"] == 0
    assert body["attendance_rate"] == 0.0
    assert body["upcoming"] == []


async def test_stats_exige_autenticacao(client, doctor) -> None:
    response = await client.get("/api/doctors/me/stats")
    assert response.status_code == 401
