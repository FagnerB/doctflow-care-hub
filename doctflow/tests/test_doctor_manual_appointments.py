"""Agendamento manual pelo médico — POST /doctors/me/appointments.

Diferente do fluxo público: pode marcar fora do expediente configurado, só
bloqueia conflito real de horário.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import settings
from app.models.appointment import Appointment
from app.models.notification_log import NotificationLog
from app.models.patient import Patient

LOCAL_TZ = ZoneInfo(settings.timezone)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def horario_futuro(dias: int = 3, hora: int = 9) -> datetime:
    alvo = (datetime.now(LOCAL_TZ) + timedelta(days=dias)).date()
    return datetime.combine(alvo, time(hora, 0), tzinfo=LOCAL_TZ)


async def test_cria_agendamento_para_paciente_novo(client, doctor, doctor_token) -> None:
    quando = horario_futuro(hora=9)  # dentro do expediente (08-12)
    response = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "scheduled_at": quando.isoformat(),
            "notes": "Encaixe pedido por telefone",
        },
        headers=auth(doctor_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["patient"]["phone"] == "+5511912345678"
    assert body["notes"] == "Encaixe pedido por telefone"


async def test_reaproveita_paciente_existente_pelo_telefone(client, session, doctor, doctor_token) -> None:
    session.add(Patient(id="patient-existente", name="Maria Antiga", phone="+5511977776666"))
    await session.commit()

    quando = horario_futuro(hora=10)
    response = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "Maria Antiga",
            "patient_phone": "(11) 97777-6666",
            "scheduled_at": quando.isoformat(),
        },
        headers=auth(doctor_token),
    )
    assert response.status_code == 201
    assert response.json()["patient_id"] == "patient-existente"

    total_pacientes = (await session.scalars(select(Patient))).all()
    assert len(total_pacientes) == 1  # não duplicou


async def test_permite_encaixe_fora_do_expediente(client, doctor, doctor_token) -> None:
    """Médico da fixture só atende 08:00-12:00 — 19:00 é fora do expediente
    e o agendamento público recusaria isso. O manual precisa aceitar."""
    quando = horario_futuro(hora=19)
    response = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "Paciente Encaixado",
            "patient_phone": "11955554444",
            "scheduled_at": quando.isoformat(),
        },
        headers=auth(doctor_token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "confirmed"


async def test_bloqueia_conflito_real_de_horario(client, doctor, doctor_token) -> None:
    quando = horario_futuro(hora=9)
    payload = {
        "patient_name": "Primeiro Paciente",
        "patient_phone": "11911112222",
        "scheduled_at": quando.isoformat(),
    }
    primeira = await client.post("/api/doctors/me/appointments", json=payload, headers=auth(doctor_token))
    assert primeira.status_code == 201

    payload["patient_name"] = "Segundo Paciente"
    payload["patient_phone"] = "11933334444"
    segunda = await client.post("/api/doctors/me/appointments", json=payload, headers=auth(doctor_token))
    assert segunda.status_code == 409
    assert "conflito" in segunda.json()["error"].lower() or "consulta ativa" in segunda.json()["error"].lower()


async def test_agendamento_manual_exige_autenticacao(client, doctor) -> None:
    response = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "Sem Login",
            "patient_phone": "11900001111",
            "scheduled_at": horario_futuro().isoformat(),
        },
    )
    assert response.status_code == 401


async def test_agendamento_manual_registra_notificacao_de_confirmacao(client, session, doctor, doctor_token) -> None:
    quando = horario_futuro(hora=11)
    response = await client.post(
        "/api/doctors/me/appointments",
        json={"patient_name": "Ana Paciente", "patient_phone": "11966665555", "scheduled_at": quando.isoformat()},
        headers=auth(doctor_token),
    )
    assert response.status_code == 201
    # Modo mock: registra a tentativa, mas não finge ter entregue de verdade.
    assert response.json()["confirmation_sent_at"] is None

    logs = (await session.scalars(select(NotificationLog))).all()
    assert [log.type.value for log in logs] == ["confirmation"]
    assert logs[0].status.value == "simulated"


async def test_agendamento_manual_com_notify_patient_falso_nao_notifica(client, session, doctor, doctor_token) -> None:
    """Importação de agenda já existente não pode disparar confirmação
    retroativa para dezenas de pacientes reais."""
    quando = horario_futuro(hora=9)
    response = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "Paciente Importado",
            "patient_phone": "11988887777",
            "scheduled_at": quando.isoformat(),
            "notify_patient": False,
        },
        headers=auth(doctor_token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["confirmation_sent_at"] is None

    logs = (await session.scalars(select(NotificationLog))).all()
    assert logs == []


async def test_agendamento_manual_de_outro_medico_nao_vaza(client, session, doctor, doctor_token) -> None:
    """O appointment criado precisa ficar sob o doctor_id de quem está logado,
    nunca de outro médico — checagem direta de isolamento por tenant."""
    quando = horario_futuro(hora=9)
    response = await client.post(
        "/api/doctors/me/appointments",
        json={"patient_name": "Teste Tenant", "patient_phone": "11988882222", "scheduled_at": quando.isoformat()},
        headers=auth(doctor_token),
    )
    appointment_id = response.json()["id"]
    saved = await session.get(Appointment, appointment_id)
    assert saved.doctor_id == doctor.id
