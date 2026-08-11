"""Webhooks de entrada do provedor de WhatsApp.

Fluxo coberto: o paciente responde "CANCELAR" na conversa, o provedor faz POST
aqui, localizamos a próxima consulta ativa pelo telefone, cancelamos e avisamos
o médico.

Segurança: este endpoint cancela consultas a partir de um número de telefone,
então ele é autenticado. Twilio → assinatura HMAC `X-Twilio-Signature`; demais
provedores → segredo compartilhado no header `X-Webhook-Secret`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import unicodedata

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_db_session, rate_limit_webhook
from app.exceptions import AppError, ForbiddenError
from app.models.common import normalize_br_phone
from app.schemas.appointment import AppointmentWebhookPayload, WebhookAckResponse
from app.services.appointment_service import appointment_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

CANCEL_KEYWORDS = {"CANCELAR", "CANCELA", "CANCEL"}


def _normalize_text(value: str) -> str:
    """Maiúsculas e sem acento, para comparar a palavra-chave com tolerância."""
    sem_acento = unicodedata.normalize("NFKD", value)
    sem_acento = "".join(character for character in sem_acento if not unicodedata.combining(character))
    return sem_acento.upper().strip()


def is_cancel_request(message: str) -> bool:
    """True se a mensagem do paciente pedir cancelamento.

    Compara por palavra inteira: "cancelar" cancela, mas uma frase como
    "não quero cancelar" também contém a palavra — aceitamos esse falso
    positivo em troca de simplicidade, já que o paciente recebe confirmação
    da ação e pode reagendar pelo mesmo link.
    """
    limpo = "".join(character if character.isalnum() else " " for character in _normalize_text(message))
    return any(palavra in CANCEL_KEYWORDS for palavra in limpo.split())


def _twilio_expected_signature(url: str, params: dict[str, str]) -> str:
    """Assinatura esperada conforme especificação da Twilio.

    URL completa + pares chave/valor concatenados em ordem alfabética de chave,
    tudo em HMAC-SHA1 com o auth token, em base64.
    """
    payload = url
    for key in sorted(params):
        payload += key + params[key]
    digest = hmac.new(
        settings.twilio_auth_token.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    return base64.b64encode(digest).decode("utf-8")


async def _authenticate_twilio(request: Request, form: dict[str, str]) -> None:
    if not settings.twilio_validate_signature:
        logger.warning("twilio_signature_validation_disabled")
        return

    if not settings.twilio_auth_token:
        raise ForbiddenError("Webhook Twilio não configurado (TWILIO_AUTH_TOKEN ausente)")

    signature = request.headers.get("x-twilio-signature")
    if not signature:
        raise ForbiddenError("Assinatura do webhook ausente")

    # A assinatura é calculada sobre a URL pública que a Twilio chamou. Atrás de
    # proxy (Railway) o request.url pode vir como http/interno, por isso o
    # TWILIO_WEBHOOK_URL explícito tem precedência.
    url = settings.twilio_webhook_url or str(request.url)
    if not hmac.compare_digest(signature, _twilio_expected_signature(url, form)):
        logger.warning("twilio_signature_mismatch", extra={"path": request.url.path})
        raise ForbiddenError("Assinatura do webhook inválida")


async def _handle_cancellation(session: AsyncSession, phone: str, message: str) -> tuple[bool, str]:
    """Processa a mensagem recebida. Retorna (cancelou, resposta_ao_paciente)."""
    if not is_cancel_request(message):
        return False, ""

    try:
        appointment = await appointment_service.cancel_by_phone(session, phone)
    except AppError as exc:
        # Não é erro de integração: o provedor deve receber 200 mesmo assim,
        # senão fica reentregando o mesmo evento. Explicamos ao paciente.
        await session.rollback()
        logger.info("webhook_cancel_rejected", extra={"phone": phone, "message": exc.message})
        return False, exc.message

    await appointment_service.send_cancellation_notifications(session, appointment)
    await session.commit()
    logger.info("webhook_cancel_done", extra={"phone": phone, "appointment_id": appointment.id})
    return True, "Sua consulta foi cancelada. Para remarcar, acesse o link de agendamento."


def _twiml(message: str) -> Response:
    """Resposta TwiML — a Twilio entrega esse texto ao paciente."""
    if not message:
        body = "<Response/>"
    else:
        escaped = (
            message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
        body = f"<Response><Message>{escaped}</Message></Response>"
    return Response(content=body, media_type="application/xml")


@router.post("/whatsapp/twilio", dependencies=[Depends(rate_limit_webhook)])
async def twilio_whatsapp_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """Webhook da Twilio (application/x-www-form-urlencoded).

    Configure em Messaging → Sandbox/Sender → "When a message comes in":
    POST https://SEU-HOST/api/webhooks/whatsapp/twilio
    """
    form_data = await request.form()
    form = {key: str(value) for key, value in form_data.items()}

    await _authenticate_twilio(request, form)

    raw_phone = form.get("From", "").replace("whatsapp:", "").strip()
    message = form.get("Body", "")
    if not raw_phone:
        return _twiml("")

    try:
        phone = normalize_br_phone(raw_phone)
    except ValueError:
        logger.info("webhook_phone_invalid", extra={"phone": raw_phone})
        return _twiml("")

    _, reply = await _handle_cancellation(session, phone, message)
    return _twiml(reply)


@router.post("/whatsapp", response_model=WebhookAckResponse, dependencies=[Depends(rate_limit_webhook)])
async def generic_whatsapp_webhook(
    payload: AppointmentWebhookPayload,
    session: AsyncSession = Depends(get_db_session),
    x_webhook_secret: str | None = Header(default=None),
) -> WebhookAckResponse:
    """Webhook genérico em JSON para provedores não-Twilio (Z-API, Evolution...).

    Protegido por `X-Webhook-Secret`, comparado com WHATSAPP_API_KEY. Sem chave
    configurada o endpoint fica desligado, para não expor cancelamento anônimo.
    """
    expected = settings.whatsapp_api_key.strip()
    if not expected:
        raise ForbiddenError("Webhook genérico desabilitado (WHATSAPP_API_KEY não configurada)")
    if not x_webhook_secret or not hmac.compare_digest(x_webhook_secret, expected):
        raise ForbiddenError("Segredo do webhook inválido")

    cancelled, reply = await _handle_cancellation(session, payload.from_phone, payload.message)
    return WebhookAckResponse(cancelled=cancelled, message=reply or "Mensagem recebida.")
