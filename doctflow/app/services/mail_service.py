"""Email transacional de conteúdo livre (confirmação/cancelamento de consulta).

Diferente de email_service.py -- que só dispara os fluxos fixos de Auth do
Supabase (recuperação de senha, convite de médico) -- aqui o conteúdo é
nosso e o destinatário não tem conta no sistema. Via SMTP genérico
(aiosmtplib) para não acoplar a nenhum SDK de provedor: Resend, Brevo e
praticamente qualquer serviço transacional expõem um endpoint SMTP.

MAIL_PROVIDER=console (padrão): modo mock, só loga -- mesmo princípio do
WhatsApp mock em notification_service.py, nunca finge ter entregue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from email.headerregistry import Address
from email.message import EmailMessage

import aiosmtplib

from app.config import settings
from app.services.notification_service import format_local_datetime

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class MailResult:
    ok: bool
    provider: str
    # True quando caiu no mock: nada foi entregue de verdade, só logado.
    simulated: bool = False
    error_message: str | None = None


class MailService:
    def __init__(self) -> None:
        self.provider = settings.mail_provider.lower().strip()

    def _smtp_configured(self) -> bool:
        return bool(settings.smtp_host and settings.smtp_user and settings.smtp_password and settings.mail_from_email)

    async def send(
        self,
        to_email: str,
        subject: str,
        body_text: str,
        from_name: str | None = None,
        reply_to: str | None = None,
    ) -> MailResult:
        if self.provider != "smtp" or not self._smtp_configured():
            reason = "SMTP_* incompleto" if self.provider == "smtp" else f"provider={self.provider}"
            # JsonLogFormatter só repassa um whitelist fixo de chaves do `extra`
            # (path/method/status_code/request_id/user_id/provider/phone) -- to/subject/
            # reason ficariam mudos no log se fossem por `extra`. Vai na mensagem.
            logger.info("mail_notification_mock to=%s subject=%r reason=%s", to_email, subject, reason)
            return MailResult(ok=True, provider="console", simulated=True)

        message = EmailMessage()
        # Address (não f-string) escapa o display name corretamente -- nomes
        # de médico podem ter parênteses/vírgula ("Dr(a). Fulano"), e montar
        # o header à mão quebra em RFC 5322 nesses casos.
        local_part, _, domain = settings.mail_from_email.partition("@")
        message["From"] = Address(display_name=from_name or settings.mail_from_name, username=local_part, domain=domain)
        message["To"] = to_email
        message["Subject"] = subject
        effective_reply_to = reply_to or settings.mail_reply_to
        if effective_reply_to:
            message["Reply-To"] = effective_reply_to
        message.set_content(body_text)

        # Porta 465 = TLS implícito; qualquer outra (587 é o normal em
        # Resend/Brevo) usa STARTTLS. Evita precisar de um env var extra só
        # pra isso.
        use_implicit_tls = settings.smtp_port == 465
        try:
            await aiosmtplib.send(
                message,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user,
                password=settings.smtp_password,
                use_tls=use_implicit_tls,
                start_tls=not use_implicit_tls,
                timeout=20,
            )
        except (aiosmtplib.SMTPException, OSError, TimeoutError) as exc:
            # Mesmo motivo do log acima: erro real precisa ir na mensagem, não em `extra`.
            logger.warning("mail_send_failed to=%s subject=%r error=%s", to_email, subject, exc)
            return MailResult(ok=False, provider="smtp", error_message=str(exc))

        return MailResult(ok=True, provider="smtp")

    # ------------------------------------------------------------------
    # Templates
    # ------------------------------------------------------------------

    @staticmethod
    def build_confirmation_email(
        patient_name: str, doctor_name: str, scheduled_at: datetime, cancel_url: str
    ) -> tuple[str, str]:
        subject = f"Consulta confirmada com Dr(a). {doctor_name}"
        body = (
            f"Olá {patient_name},\n\n"
            f"Sua consulta com Dr(a). {doctor_name} está confirmada para "
            f"{format_local_datetime(scheduled_at)}.\n\n"
            f"Para cancelar, acesse: {cancel_url}\n\n"
            "Dúvidas? É só responder este email."
        )
        return subject, body


mail_service = MailService()
