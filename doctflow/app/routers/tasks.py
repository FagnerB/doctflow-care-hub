"""Endpoints operacionais para acionamento por cron externo."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header

from app.config import settings
from app.exceptions import ForbiddenError
from app.schemas.appointment import ReminderRunResponse
from app.tasks.reminder_jobs import run_reminders_once

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def require_cron_secret(x_cron_secret: str | None = Header(default=None)) -> None:
    """Autentica o cron por segredo compartilhado.

    Um cron externo não tem JWT de owner, então usamos header dedicado. Sem
    CRON_SECRET configurado o endpoint fica desligado — nunca aberto.
    """
    if not settings.cron_secret:
        raise ForbiddenError("Endpoint de cron desabilitado (CRON_SECRET não configurado)")
    if not x_cron_secret or not _secure_equals(x_cron_secret, settings.cron_secret):
        raise ForbiddenError("Segredo de cron inválido")


def _secure_equals(left: str, right: str) -> bool:
    # Comparação em tempo constante evita vazar o segredo por timing.
    import hmac

    return hmac.compare_digest(left, right)


@router.post("/reminders/run", response_model=ReminderRunResponse, dependencies=[Depends(require_cron_secret)])
async def run_reminders_endpoint() -> ReminderRunResponse:
    """Dispara uma passada de lembretes (24h e 2h).

    Idempotente: consultas já notificadas são ignoradas via notification_logs,
    então pode ser chamado com frequência sem risco de mensagem duplicada.
    """
    sent, failed = await run_reminders_once()
    return ReminderRunResponse(sent=sent, failed=failed)
