"""Serviço de e-mails transacionais.

Todo o envio é delegado ao Supabase Auth (ele já hospeda os templates de
recuperação e de convite), então aqui só montamos as chamadas administrativas.
Sem Supabase configurado o serviço entra em *mock mode* e apenas loga — assim o
fluxo de desenvolvimento não trava.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import settings
from app.exceptions import AppError

logger = logging.getLogger(__name__)


class EmailDeliveryError(AppError):
    def __init__(self, message: str = "Falha ao enviar e-mail") -> None:
        super().__init__(message, code="email_delivery_error", status_code=502)


@dataclass(slots=True)
class EmailResult:
    ok: bool
    provider: str
    error_message: str | None = None


class EmailService:
    """Wrapper fino sobre os endpoints de e-mail do Supabase Auth."""

    def is_configured(self) -> bool:
        return bool(settings.supabase_url and settings.supabase_anon_key)

    def _base_url(self) -> str:
        return settings.supabase_url.rstrip("/")

    def _anon_headers(self) -> dict[str, str]:
        return {"apikey": settings.supabase_anon_key, "Content-Type": "application/json"}

    def _admin_headers(self) -> dict[str, str]:
        return {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }

    def _mock(self, kind: str, email: str, **extra: Any) -> EmailResult:
        logger.info("email_mock", extra={"provider": "console", "kind": kind, "email": email, **extra})
        return EmailResult(ok=True, provider="console")

    async def send_password_recovery(self, email: str) -> EmailResult:
        """Dispara o e-mail de recuperação de senha do Supabase.

        Nunca levanta erro por e-mail inexistente: quem chama devolve sempre a
        mesma resposta genérica para não permitir enumeração de contas.
        """
        if not self.is_configured():
            return self._mock("password_recovery", email, redirect_to=settings.password_reset_url)

        url = f"{self._base_url()}/auth/v1/recover"
        payload = {"email": email, "redirect_to": settings.password_reset_url}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=self._anon_headers(), json=payload)
        except httpx.HTTPError as exc:
            logger.warning("email_recovery_transport_error", extra={"email": email})
            return EmailResult(ok=False, provider="supabase", error_message=str(exc))

        if response.is_success:
            return EmailResult(ok=True, provider="supabase")

        logger.warning(
            "email_recovery_failed",
            extra={"email": email, "status_code": response.status_code},
        )
        return EmailResult(ok=False, provider="supabase", error_message=response.text)

    async def send_doctor_invite(self, email: str) -> EmailResult:
        """Convite de primeiro acesso: o médico recebe o link para definir a senha."""
        if not (self.is_configured() and settings.supabase_service_role_key):
            return self._mock("doctor_invite", email, redirect_to=settings.password_reset_url)

        url = f"{self._base_url()}/auth/v1/invite"
        payload = {"email": email, "redirect_to": settings.password_reset_url}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=self._admin_headers(), json=payload)
        except httpx.HTTPError as exc:
            return EmailResult(ok=False, provider="supabase", error_message=str(exc))

        if response.is_success:
            return EmailResult(ok=True, provider="supabase")
        return EmailResult(ok=False, provider="supabase", error_message=response.text)


email_service = EmailService()
