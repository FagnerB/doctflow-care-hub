from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from app.config import settings
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DeliveryResult:
    ok: bool
    provider: str
    error_message: str | None = None


class NotificationService:
    def __init__(self) -> None:
        self.provider = settings.whatsapp_provider.lower().strip()

    async def send_whatsapp(self, phone: str, message: str) -> DeliveryResult:
        if not self._has_external_key():
            return self._mock_send(phone, message)

        return await self._send_via_configured_provider(phone, message)

    def _has_external_key(self) -> bool:
        return bool(settings.whatsapp_api_key.strip())

    def _mock_send(self, phone: str, message: str) -> DeliveryResult:
        # Modo MVP: sem chave externa, apenas loga para não bloquear o fluxo.
        logger.info(
            "whatsapp_notification_mock",
            extra={"phone": phone, "message": message, "provider": "console"},
        )
        return DeliveryResult(ok=True, provider="console")

    async def _send_via_configured_provider(self, phone: str, message: str) -> DeliveryResult:
        if self.provider == "twilio":
            return await self._send_via_twilio(phone, message)

        return await self._send_via_http_api(phone, message)

    async def _send_via_http_api(self, phone: str, message: str) -> DeliveryResult:
        if not settings.whatsapp_api_url.strip():
            return DeliveryResult(ok=False, provider="http_api", error_message="WHATSAPP_API_URL não configurada")

        payload = {"to": phone, "message": message}
        headers = {
            "Authorization": f"Bearer {settings.whatsapp_api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(settings.whatsapp_api_url, json=payload, headers=headers)

        if response.is_success:
            return DeliveryResult(ok=True, provider="http_api")

        return DeliveryResult(ok=False, provider="http_api", error_message=response.text)

    async def _send_via_twilio(self, phone: str, message: str) -> DeliveryResult:
        if not (settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_whatsapp_from):
            return DeliveryResult(ok=False, provider="twilio", error_message="Credenciais Twilio não configuradas")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
        payload = {
            "From": settings.twilio_whatsapp_from,
            "To": f"whatsapp:{phone}",
            "Body": message,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, data=payload, auth=(settings.twilio_account_sid, settings.twilio_auth_token))
        if response.is_success:
            return DeliveryResult(ok=True, provider="twilio")
        return DeliveryResult(ok=False, provider="twilio", error_message=response.text)

    @staticmethod
    def build_confirmation_message(patient_name: str, doctor_name: str, scheduled_at: datetime, address: str = "Endereço informado pela clínica") -> str:
        local = scheduled_at.strftime("%d/%m/%Y às %H:%M")
        return (
            f"Olá {patient_name}, sua consulta com Dr. {doctor_name} está confirmada para {local}. "
            f"Endereço: {address}. Para cancelar, responda CANCELAR."
        )

    @staticmethod
    def build_doctor_booking_message(patient_name: str, scheduled_at: datetime) -> str:
        local = scheduled_at.strftime("%d/%m/%Y às %H:%M")
        return f"Nova consulta confirmada: {patient_name} - {local}. Ver em: {settings.dashboard_url}"

    @staticmethod
    def build_cancellation_message(patient_name: str, scheduled_at: datetime) -> str:
        local = scheduled_at.strftime("%d/%m/%Y às %H:%M")
        return f"Sua consulta de {patient_name} em {local} foi cancelada."

    @staticmethod
    def build_reminder_message(patient_name: str, doctor_name: str, scheduled_at: datetime, hours_ahead: int) -> str:
        local = scheduled_at.strftime("%d/%m/%Y às %H:%M")
        return f"Lembrete: sua consulta com Dr. {doctor_name} para {patient_name} está agendada em {hours_ahead}h, no dia {local}."
