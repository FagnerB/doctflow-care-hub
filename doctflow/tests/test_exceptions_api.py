"""Bloqueio de dias/horários pelo médico (schedule_exceptions)."""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import settings

LOCAL_TZ = ZoneInfo(settings.timezone)


def data_futura(dias: int = 3):
    return (datetime.now(LOCAL_TZ) + timedelta(days=dias)).date()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_bloqueio_de_dia_inteiro_zera_disponibilidade(client, doctor, doctor_token) -> None:
    alvo = data_futura()

    antes = await client.get(f"/api/doctors/dr-silva/availability?date={alvo.isoformat()}")
    assert len(antes.json()["slots"]) == 8

    criado = await client.post(
        "/api/doctors/me/exceptions",
        json={"exception_date": alvo.isoformat(), "reason": "Férias"},
        headers=auth(doctor_token),
    )
    assert criado.status_code == 201, criado.text

    depois = await client.get(f"/api/doctors/dr-silva/availability?date={alvo.isoformat()}")
    assert depois.json()["slots"] == []


async def test_bloqueio_parcial_remove_apenas_a_faixa(client, doctor, doctor_token) -> None:
    alvo = data_futura()
    criado = await client.post(
        "/api/doctors/me/exceptions",
        json={
            "exception_date": alvo.isoformat(),
            "start_time": "09:00",
            "end_time": "10:00",
            "reason": "Reunião",
        },
        headers=auth(doctor_token),
    )
    assert criado.status_code == 201

    slots = (await client.get(f"/api/doctors/dr-silva/availability?date={alvo.isoformat()}")).json()["slots"]
    horas = [datetime.fromisoformat(slot["start_time"]).strftime("%H:%M") for slot in slots]
    assert "09:00" not in horas and "09:30" not in horas
    assert "08:00" in horas and "10:00" in horas
    assert len(slots) == 6


async def test_agendar_em_dia_bloqueado_falha(client, doctor, doctor_token) -> None:
    alvo = data_futura()
    await client.post(
        "/api/doctors/me/exceptions",
        json={"exception_date": alvo.isoformat()},
        headers=auth(doctor_token),
    )
    quando = datetime.combine(alvo, time(9, 0), tzinfo=LOCAL_TZ)
    response = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "desired_datetime": quando.isoformat(),
        },
    )
    assert response.status_code == 409


async def test_bloqueio_recusado_quando_ha_consulta_ativa(client, doctor, doctor_token) -> None:
    alvo = data_futura()
    quando = datetime.combine(alvo, time(9, 0), tzinfo=LOCAL_TZ)
    agendada = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": "11912345678",
            "desired_datetime": quando.isoformat(),
        },
    )
    assert agendada.status_code == 201

    bloqueio = await client.post(
        "/api/doctors/me/exceptions",
        json={"exception_date": alvo.isoformat(), "reason": "Férias"},
        headers=auth(doctor_token),
    )
    assert bloqueio.status_code == 409
    assert "consulta" in bloqueio.json()["error"].lower()


async def test_faixa_invalida_e_rejeitada(client, doctor, doctor_token) -> None:
    alvo = data_futura()
    response = await client.post(
        "/api/doctors/me/exceptions",
        json={"exception_date": alvo.isoformat(), "start_time": "11:00", "end_time": "09:00"},
        headers=auth(doctor_token),
    )
    assert response.status_code == 422


async def test_horario_isolado_sem_par_e_rejeitado(client, doctor, doctor_token) -> None:
    alvo = data_futura()
    response = await client.post(
        "/api/doctors/me/exceptions",
        json={"exception_date": alvo.isoformat(), "start_time": "09:00"},
        headers=auth(doctor_token),
    )
    assert response.status_code == 422


async def test_listar_e_remover_bloqueio(client, doctor, doctor_token) -> None:
    alvo = data_futura()
    criado = await client.post(
        "/api/doctors/me/exceptions",
        json={"exception_date": alvo.isoformat()},
        headers=auth(doctor_token),
    )
    exception_id = criado.json()["id"]

    listagem = await client.get("/api/doctors/me/exceptions", headers=auth(doctor_token))
    assert len(listagem.json()) == 1

    removido = await client.delete(f"/api/doctors/me/exceptions/{exception_id}", headers=auth(doctor_token))
    assert removido.status_code == 200

    depois = await client.get(f"/api/doctors/dr-silva/availability?date={alvo.isoformat()}")
    assert len(depois.json()["slots"]) == 8


async def test_bloqueio_exige_autenticacao(client, doctor) -> None:
    response = await client.post(
        "/api/doctors/me/exceptions",
        json={"exception_date": data_futura().isoformat()},
    )
    assert response.status_code == 401


async def test_perfil_do_medico_nao_e_confundido_com_slug(client, doctor, doctor_token) -> None:
    """Regressão: /doctors/me chegava a cair na rota pública /doctors/{slug}."""
    response = await client.get("/api/doctors/me", headers=auth(doctor_token))
    assert response.status_code == 200
    assert response.json()["slug"] == "dr-silva"
    assert response.json()["user"]["email"] == "dr.silva@example.com"
