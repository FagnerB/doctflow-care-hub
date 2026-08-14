"""MailService: mock nunca finge ter entregue, SMTP real usa as credenciais certas."""

from __future__ import annotations

import aiosmtplib

from app.config import settings
from app.services.mail_service import MailService


async def test_provider_console_e_sempre_simulado(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mail_provider", "console")
    service = MailService()
    result = await service.send("paciente@example.com", "Assunto", "Corpo")
    assert result.ok is True
    assert result.simulated is True
    assert result.provider == "console"


async def test_provider_smtp_sem_credenciais_cai_pro_mock(monkeypatch) -> None:
    """Se esqueceu de configurar alguma SMTP_* var, tem que falhar pro mock,
    nunca tentar mandar sem credencial completa."""
    monkeypatch.setattr(settings, "mail_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "")
    service = MailService()
    result = await service.send("paciente@example.com", "Assunto", "Corpo")
    assert result.simulated is True


async def test_provider_smtp_envia_de_verdade(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mail_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "user")
    monkeypatch.setattr(settings, "smtp_password", "senha")
    monkeypatch.setattr(settings, "mail_from_email", "contato@exemplo.com")
    monkeypatch.setattr(settings, "mail_from_name", "DoctFlow")

    captured = {}

    async def fake_send(message, **kwargs):
        captured["message"] = message
        captured["kwargs"] = kwargs
        return None, None

    monkeypatch.setattr(aiosmtplib, "send", fake_send)

    service = MailService()
    result = await service.send(
        "paciente@example.com",
        "Consulta confirmada",
        "corpo do email",
        from_name="Dr(a). Ana Silva",
        reply_to="dr.silva@example.com",
    )

    assert result.ok is True
    assert result.simulated is False
    assert result.provider == "smtp"
    # Address escapa o display name (tem parênteses) -- formato correto por RFC 5322.
    assert captured["message"]["From"] == '"Dr(a). Ana Silva" <contato@exemplo.com>'
    assert captured["message"]["Reply-To"] == "dr.silva@example.com"
    assert captured["kwargs"]["hostname"] == "smtp.exemplo.com"
    assert captured["kwargs"]["start_tls"] is True
    assert captured["kwargs"]["use_tls"] is False


async def test_provider_smtp_falha_de_envio_nao_derruba(monkeypatch) -> None:
    monkeypatch.setattr(settings, "mail_provider", "smtp")
    monkeypatch.setattr(settings, "smtp_host", "smtp.exemplo.com")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "user")
    monkeypatch.setattr(settings, "smtp_password", "senha")
    monkeypatch.setattr(settings, "mail_from_email", "contato@exemplo.com")

    async def fake_send_falha(message, **kwargs):
        raise aiosmtplib.SMTPConnectError("conexao recusada")

    monkeypatch.setattr(aiosmtplib, "send", fake_send_falha)

    service = MailService()
    result = await service.send("paciente@example.com", "Assunto", "Corpo")

    assert result.ok is False
    assert result.simulated is False
    assert result.error_message is not None
