"""Job de lembretes automáticos de consulta.

Há duas formas de acionar, e elas podem conviver (o NotificationLog garante
idempotência, então nenhum paciente recebe lembrete duplicado):

1. Scheduler interno (`REMINDERS_SCHEDULER_ENABLED=true`): uma task asyncio
   roda junto da API a cada `REMINDERS_INTERVAL_MINUTES`. É o padrão e basta
   para o MVP em uma única instância no Railway.
2. Endpoint de cron (`POST /api/tasks/reminders/run` com `X-Cron-Secret`):
   para acionar por cron externo. Recomendado se um dia a API rodar com mais
   de uma réplica — aí desligue o scheduler interno para não duplicar trabalho.
"""

from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.appointment_service import appointment_service

logger = logging.getLogger(__name__)


async def run_reminders_once() -> tuple[int, int]:
    """Executa uma passada de lembretes usando sessão própria.

    Abre e fecha a própria sessão porque roda fora do ciclo de request.
    """
    async with AsyncSessionLocal() as session:
        try:
            sent, failed = await appointment_service.run_reminders(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    logger.info("reminders_run_finished", extra={"sent": sent, "failed": failed})
    return sent, failed


class ReminderScheduler:
    """Loop assíncrono simples que dispara os lembretes periodicamente.

    Preferido a APScheduler/Celery para não adicionar dependência nem broker:
    o MVP roda em um único container e a idempotência já está no banco.
    """

    def __init__(self, interval_minutes: int | None = None) -> None:
        self.interval_seconds = (interval_minutes or settings.reminders_interval_minutes) * 60
        self._task: asyncio.Task[None] | None = None

    async def _loop(self) -> None:
        # Pequeno atraso inicial para não competir com o boot da aplicação.
        await asyncio.sleep(10)
        while True:
            try:
                await run_reminders_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Um erro (banco fora do ar, provider instável) não pode matar
                # o loop: loga e tenta de novo no próximo ciclo.
                logger.exception("reminders_run_failed")
            await asyncio.sleep(self.interval_seconds)

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop(), name="doctflow-reminders")
        logger.info("reminders_scheduler_started", extra={"interval_seconds": self.interval_seconds})

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
        logger.info("reminders_scheduler_stopped")
