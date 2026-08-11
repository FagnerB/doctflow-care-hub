"""Fluxo público de agendamento ponta a ponta."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import settings
from app.models.notification_log import NotificationLog

LOCAL_TZ = ZoneInfo(settings.timezone)


def proximo_slot(dias_a_frente: int = 2, hora: int = 9) -> datetime:
    """Um horário dentro da agenda da fixture (08:00–12:00), sempre no futuro."""
    alvo = (datetime.now(LOCAL_TZ) + timedelta(days=dias_a_frente)).date()
    return datetime.combine(alvo, time(hora, 0), tzinfo=LOCAL_TZ)


async def test_perfil_publico_do_medico(client, doctor) -> None:
    response = await client.get("/api/doctors/dr-silva")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "dr-silva"
    assert body["full_name"] == "Ana Silva"
    assert body["specialty"] == "Cardiologia"


async def test_disponibilidade_lista_slots_do_dia(client, doctor) -> None:
    alvo = proximo_slot().date()
    response = await client.get(f"/api/doctors/dr-silva/availability?date={alvo.isoformat()}")
    assert response.status_code == 200
    slots = response.json()["slots"]
    # 08:00–12:00 em blocos de 30 min = 8 slots.
    assert len(slots) == 8
    assert all(slot["is_available"] for slot in slots)


async def test_agendamento_publico_confirma_e_registra_notificacao(client, doctor, session) -> None:
    quando = proximo_slot()
    response = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "(11) 91234-5678",
            "desired_datetime": quando.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "confirmed"
    assert body["duration_minutes"] == 30
    assert body["patient"]["phone"] == "+5511912345678"
    assert body["confirmation_sent_at"] is not None

    # A confirmação (modo mock) precisa ficar registrada em notification_logs.
    logs = (await session.scalars(select(NotificationLog))).all()
    assert [log.type.value for log in logs] == ["confirmation"]
    assert logs[0].status.value == "sent"


async def test_slot_some_da_disponibilidade_apos_agendar(client, doctor) -> None:
    quando = proximo_slot()
    await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "desired_datetime": quando.isoformat(),
        },
    )
    response = await client.get(f"/api/doctors/dr-silva/availability?date={quando.date().isoformat()}")
    horarios = [slot["start_time"] for slot in response.json()["slots"]]
    assert quando.isoformat() not in horarios
    assert len(horarios) == 7


async def test_agendamento_duplicado_no_mesmo_horario_conflita(client, doctor) -> None:
    quando = proximo_slot()
    payload = {
        "doctor_slug": "dr-silva",
        "patient_name": "Carlos Souza",
        "patient_phone": "11912345678",
        "desired_datetime": quando.isoformat(),
    }
    assert (await client.post("/api/appointments", json=payload)).status_code == 201

    payload["patient_name"] = "Maria Lima"
    payload["patient_phone"] = "11955554444"
    segunda = await client.post("/api/appointments", json=payload)
    assert segunda.status_code == 409
    assert segunda.json()["error"] == "Horário indisponível"


async def test_recusa_horario_fora_do_expediente(client, doctor) -> None:
    fora = proximo_slot(hora=15)  # agenda vai só até 12:00
    response = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "desired_datetime": fora.isoformat(),
        },
    )
    assert response.status_code == 409


async def test_recusa_horario_no_passado(client, doctor) -> None:
    ontem = datetime.combine((datetime.now(LOCAL_TZ) - timedelta(days=1)).date(), time(9, 0), tzinfo=LOCAL_TZ)
    response = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "desired_datetime": ontem.isoformat(),
        },
    )
    assert response.status_code == 400
    assert "passado" in response.json()["error"].lower()


async def test_recusa_alem_da_janela_de_agendamento(client, doctor) -> None:
    distante = proximo_slot(dias_a_frente=60)
    response = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "desired_datetime": distante.isoformat(),
        },
    )
    assert response.status_code == 400


async def test_status_publico_da_consulta(client, doctor) -> None:
    quando = proximo_slot()
    criada = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "desired_datetime": quando.isoformat(),
        },
    )
    appointment_id = criada.json()["id"]
    response = await client.get(f"/api/appointments/{appointment_id}/status")
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"


async def test_medico_inexistente_retorna_404(client) -> None:
    response = await client.get("/api/doctors/nao-existe")
    assert response.status_code == 404
