"""Envio de mensagens de WhatsApp e montagem dos textos enviados.

Providers suportados:
- `console` (padrão): modo mock, apenas loga. Usado quando não há credencial.
- `twilio`: Twilio WhatsApp (o sandbox gratuito serve para testes).
- `http_api`: qualquer gateway REST simples (Z-API, Evolution, etc.).

O modo mock é escolhido automaticamente quando o provider configurado está sem
credenciais, para que o MVP nunca trave por falta de integração.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def format_local_datetime(value: datetime) -> str:
    """Formata um instante no fuso do consultório.

    `scheduled_at` é persistido em UTC; formatar sem converter mostraria ao
    paciente um horário 3 horas adiantado.
    """
    local_tz = ZoneInfo(settings.timezone)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(local_tz).strftime("%d/%m/%Y às %H:%M")


@dataclass(slots=True)
class DeliveryResult:
    ok: bool
    provider: str
    error_message: str | None = None


class NotificationService:
    def __init__(self) -> None:
        self.provider = settings.whatsapp_provider.lower().strip()

    async def send_whatsapp(self, phone: str, message: str) -> DeliveryResult:
        if not phone:
            return DeliveryResult(ok=False, provider=self.provider, error_message="Telefone ausente")

        if self.provider == "twilio":
            if not self._twilio_configured():
                return self._mock_send(phone, message, reason="credenciais Twilio ausentes")
            return await self._send_via_twilio(phone, message)

        if self.provider == "http_api":
            if not self._http_api_configured():
                return self._mock_send(phone, message, reason="WHATSAPP_API_URL/KEY ausentes")
            return await self._send_via_http_api(phone, message)

        return self._mock_send(phone, message)

    @staticmethod
    def _twilio_configured() -> bool:
        return bool(settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_from)

    @staticmethod
    def _http_api_configured() -> bool:
        return bool(settings.whatsapp_api_url.strip() and settings.whatsapp_api_key.strip())

    def _mock_send(self, phone: str, message: str, reason: str | None = None) -> DeliveryResult:
        # Modo MVP: sem credencial, apenas loga para não bloquear o fluxo.
        logger.info(
            "whatsapp_notification_mock",
            # "message" é chave reservada do próprio módulo logging (colide com
            # LogRecord.message) — usar esse nome em `extra` sempre lança KeyError.
            extra={"phone": phone, "whatsapp_message": message, "provider": "console", "reason": reason},
        )
        return DeliveryResult(ok=True, provider="console")

    async def _send_via_http_api(self, phone: str, message: str) -> DeliveryResult:
        payload = {"to": phone, "message": message}
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(settings.whatsapp_api_url, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            return DeliveryResult(ok=False, provider="http_api", error_message=str(exc))

        if response.is_success:
            return DeliveryResult(ok=True, provider="http_api")
        return DeliveryResult(ok=False, provider="http_api", error_message=response.text[:500])

    async def _send_via_twilio(self, phone: str, message: str) -> DeliveryResult:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
        sender = settings.twilio_whatsapp_from
        if not sender.startswith("whatsapp:"):
            sender = f"whatsapp:{sender}"
        payload = {"From": sender, "To": f"whatsapp:{phone}", "Body": message}
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(
                    url, data=payload, auth=(settings.twilio_account_sid, settings.twilio_auth_token)
                )
        except httpx.HTTPError as exc:
            return DeliveryResult(ok=False, provider="twilio", error_message=str(exc))

        if response.is_success:
            return DeliveryResult(ok=True, provider="twilio")
        return DeliveryResult(ok=False, provider="twilio", error_message=response.text[:500])

    # ------------------------------------------------------------------
    # Templates de mensagem
    # ------------------------------------------------------------------

    @staticmethod
    def build_confirmation_message(patient_name: str, doctor_name: str, scheduled_at: datetime) -> str:
        """Confirmação enviada ao paciente logo após o agendamento."""
        return (
            f"Olá {patient_name}, sua consulta com Dr(a). {doctor_name} está confirmada "
            f"para {format_local_datetime(scheduled_at)}. Para cancelar, responda CANCELAR."
        )

    @staticmethod
    def build_doctor_booking_message(patient_name: str, patient_phone: str, scheduled_at: datetime) -> str:
        """Aviso ao médico de que chegou um novo agendamento."""
        return (
            f"Nova consulta: {patient_name} ({patient_phone}) - {format_local_datetime(scheduled_at)}. "
            f"Ver em: {settings.dashboard_url}"
        )

    @staticmethod
    def build_patient_cancellation_message(doctor_name: str, scheduled_at: datetime) -> str:
        """Recibo de cancelamento enviado ao paciente."""
        return (
            f"Sua consulta com Dr(a). {doctor_name} em {format_local_datetime(scheduled_at)} foi cancelada. "
            "Se quiser remarcar, é só acessar o link de agendamento novamente."
        )

    @staticmethod
    def build_doctor_cancellation_message(patient_name: str, scheduled_at: datetime) -> str:
        """Aviso ao médico de que o paciente cancelou."""
        return (
            f"O paciente {patient_name} cancelou a consulta de {format_local_datetime(scheduled_at)}. "
            f"O horário já está liberado na agenda: {settings.dashboard_url}"
        )

    @staticmethod
    def build_reminder_message(patient_name: str, doctor_name: str, scheduled_at: datetime, hours_ahead: int) -> str:
        """Lembrete enviado ao paciente 24h e 2h antes."""
        quando = "amanhã" if hours_ahead >= 24 else f"em aproximadamente {hours_ahead}h"
        return (
            f"Olá {patient_name}, lembrete da sua consulta com Dr(a). {doctor_name} {quando}, "
            f"em {format_local_datetime(scheduled_at)}. Para cancelar, responda CANCELAR."
        )


notification_service = NotificationService()
