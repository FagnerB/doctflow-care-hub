"""Webhook de WhatsApp: autenticação e cancelamento pelo paciente."""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.appointment import Appointment
from app.models.notification_log import NotificationLog
from app.routers.webhooks import is_cancel_request

LOCAL_TZ = ZoneInfo(settings.timezone)

# Router desligado em app/main.py: cancel_by_phone identifica o paciente só
# pelo telefone, sem checar doctor_id, e pode cancelar a consulta do médico
# errado. Religar estes testes junto com o router quando isso for resolvido.
pytestmark = pytest.mark.skip(reason="webhooks.router desligado -- ver app/main.py")


def slot_futuro(dias: int = 5, hora: int = 9) -> datetime:
    alvo = (datetime.now(LOCAL_TZ) + timedelta(days=dias)).date()
    return datetime.combine(alvo, time(hora, 0), tzinfo=LOCAL_TZ)


async def agendar(client, telefone: str = "11912345678", dias: int = 5) -> dict:
    quando = slot_futuro(dias=dias)
    response = await client.post(
        "/api/appointments",
        json={
            "doctor_slug": "dr-silva",
            "patient_name": "Carlos Souza",
            "patient_phone": telefone,
            "desired_datetime": quando.isoformat(),
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Detecção da palavra-chave
# --------------------------------------------------------------------------


@pytest.mark.parametrize("texto", ["CANCELAR", "cancelar", "Cancelar!", "quero cancelar", "  cancela  "])
def test_reconhece_pedido_de_cancelamento(texto: str) -> None:
    assert is_cancel_request(texto) is True


@pytest.mark.parametrize("texto", ["oi", "confirmar", "obrigado", "que horas é a consulta?"])
def test_ignora_mensagens_comuns(texto: str) -> None:
    assert is_cancel_request(texto) is False


# --------------------------------------------------------------------------
# Webhook genérico (JSON + segredo compartilhado)
# --------------------------------------------------------------------------


async def test_webhook_generico_exige_segredo(client, doctor, monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_api_key", "segredo-super")
    await agendar(client)

    response = await client.post(
        "/api/webhooks/whatsapp",
        json={"from_phone": "11912345678", "message": "CANCELAR"},
    )
    assert response.status_code == 403


async def test_webhook_generico_rejeita_segredo_errado(client, doctor, monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_api_key", "segredo-super")
    await agendar(client)

    response = await client.post(
        "/api/webhooks/whatsapp",
        json={"from_phone": "11912345678", "message": "CANCELAR"},
        headers={"X-Webhook-Secret": "errado"},
    )
    assert response.status_code == 403


async def test_webhook_desabilitado_sem_chave_configurada(client, doctor, monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_api_key", "")
    response = await client.post(
        "/api/webhooks/whatsapp",
        json={"from_phone": "11912345678", "message": "CANCELAR"},
        headers={"X-Webhook-Secret": "qualquer"},
    )
    assert response.status_code == 403


async def test_cancelamento_via_webhook_generico(client, doctor, session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_api_key", "segredo-super")
    criada = await agendar(client)

    response = await client.post(
        "/api/webhooks/whatsapp",
        json={"from_phone": "(11) 91234-5678", "message": "CANCELAR"},
        headers={"X-Webhook-Secret": "segredo-super"},
    )
    assert response.status_code == 200
    assert response.json()["cancelled"] is True

    appointment = await session.get(Appointment, criada["id"])
    await session.refresh(appointment)
    assert appointment.status.value == "cancelled_by_patient"

    # Precisa registrar o log de cancelamento (paciente + aviso ao médico).
    logs = (await session.scalars(select(NotificationLog))).all()
    assert "cancellation" in [log.type.value for log in logs]


async def test_mensagem_qualquer_nao_cancela(client, doctor, session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_api_key", "segredo-super")
    criada = await agendar(client)

    response = await client.post(
        "/api/webhooks/whatsapp",
        json={"from_phone": "11912345678", "message": "obrigado, até lá!"},
        headers={"X-Webhook-Secret": "segredo-super"},
    )
    assert response.status_code == 200
    assert response.json()["cancelled"] is False

    appointment = await session.get(Appointment, criada["id"])
    await session.refresh(appointment)
    assert appointment.status.value == "confirmed"


async def test_horario_liberado_apos_cancelamento(client, doctor, monkeypatch) -> None:
    monkeypatch.setattr(settings, "whatsapp_api_key", "segredo-super")
    quando = slot_futuro()
    await agendar(client)

    await client.post(
        "/api/webhooks/whatsapp",
        json={"from_phone": "11912345678", "message": "CANCELAR"},
        headers={"X-Webhook-Secret": "segredo-super"},
    )

    slots = (await client.get(f"/api/doctors/dr-silva/availability?date={quando.date().isoformat()}")).json()["slots"]
    assert quando.isoformat() in [slot["start_time"] for slot in slots]


async def test_politica_de_cancelamento_bloqueia_em_cima_da_hora(client, doctor, session, monkeypatch) -> None:
    """A fixture usa cancellation_policy_hours=24; uma consulta amanhã cedo já passou do prazo."""
    monkeypatch.setattr(settings, "whatsapp_api_key", "segredo-super")

    # Agenda para daqui a poucas horas gravando direto (a API exigiria slot livre futuro).
    # Em UTC, como faz o serviço: no SQLite a coluna guarda o texto do datetime e
    # misturar offsets quebraria a comparação da query.
    quando = datetime.now(timezone.utc) + timedelta(hours=3)
    session.add(
        Appointment(
            id="appt-curto-prazo",
            doctor_id=doctor.id,
            patient_id=(await _criar_paciente(session)).id,
            scheduled_at=quando,
            duration_minutes=30,
            status="confirmed",
        )
    )
    await session.commit()

    response = await client.post(
        "/api/webhooks/whatsapp",
        json={"from_phone": "11912345678", "message": "CANCELAR"},
        headers={"X-Webhook-Secret": "segredo-super"},
    )
    assert response.status_code == 200
    assert response.json()["cancelled"] is False
    assert "24h" in response.json()["message"]


async def _criar_paciente(session):
    from app.models.patient import Patient

    patient = Patient(id="patient-1", name="Carlos Souza", phone="+5511912345678")
    session.add(patient)
    await session.flush()
    return patient


# --------------------------------------------------------------------------
# Webhook Twilio (form + assinatura HMAC)
# --------------------------------------------------------------------------


def assinatura_twilio(url: str, params: dict[str, str], token: str) -> str:
    payload = url + "".join(key + params[key] for key in sorted(params))
    digest = hmac.new(token.encode(), payload.encode(), hashlib.sha1).digest()
    return base64.b64encode(digest).decode()


async def test_twilio_rejeita_sem_assinatura(client, doctor, monkeypatch) -> None:
    monkeypatch.setattr(settings, "twilio_auth_token", "token-teste")
    monkeypatch.setattr(settings, "twilio_validate_signature", True)

    response = await client.post(
        "/api/webhooks/whatsapp/twilio",
        data={"From": "whatsapp:+5511912345678", "Body": "CANCELAR"},
    )
    assert response.status_code == 403


async def test_twilio_rejeita_assinatura_invalida(client, doctor, monkeypatch) -> None:
    monkeypatch.setattr(settings, "twilio_auth_token", "token-teste")
    monkeypatch.setattr(settings, "twilio_validate_signature", True)

    response = await client.post(
        "/api/webhooks/whatsapp/twilio",
        data={"From": "whatsapp:+5511912345678", "Body": "CANCELAR"},
        headers={"X-Twilio-Signature": "assinatura-falsa"},
    )
    assert response.status_code == 403


async def test_twilio_cancela_com_assinatura_valida(client, doctor, session, monkeypatch) -> None:
    url = "http://test/api/webhooks/whatsapp/twilio"
    monkeypatch.setattr(settings, "twilio_auth_token", "token-teste")
    monkeypatch.setattr(settings, "twilio_validate_signature", True)
    monkeypatch.setattr(settings, "twilio_webhook_url", url)

    criada = await agendar(client)
    form = {"From": "whatsapp:+5511912345678", "Body": "CANCELAR"}

    response = await client.post(
        "/api/webhooks/whatsapp/twilio",
        data=form,
        headers={"X-Twilio-Signature": assinatura_twilio(url, form, "token-teste")},
    )
    assert response.status_code == 200
    assert "cancelada" in response.text
    assert response.headers["content-type"].startswith("application/xml")

    appointment = await session.get(Appointment, criada["id"])
    await session.refresh(appointment)
    assert appointment.status.value == "cancelled_by_patient"
