from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import engine
from app.exceptions import AppError
from app.routers import admin, appointments, auth, doctors, patients, schedules, tasks

# webhooks: import comentado junto com o router abaixo -- ver motivo lá.
from app.tasks.reminder_jobs import ReminderScheduler


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        for key in ("path", "method", "status_code", "request_id", "user_id", "provider", "phone"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json_dumps(payload)


def json_dumps(payload: dict[str, object]) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    # Scheduler interno de lembretes. Desligue (REMINDERS_SCHEDULER_ENABLED=false)
    # se for acionar por cron externo ou rodar mais de uma réplica da API.
    scheduler: ReminderScheduler | None = None
    if settings.reminders_scheduler_enabled:
        scheduler = ReminderScheduler()
        scheduler.start()

    try:
        yield
    finally:
        if scheduler is not None:
            await scheduler.stop()
        await engine.dispose()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(doctors.router, prefix=settings.api_prefix)
app.include_router(patients.router, prefix=settings.api_prefix)
app.include_router(appointments.router, prefix=settings.api_prefix)
app.include_router(schedules.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
# Desligado por enquanto: cancel_by_phone (chamado por este webhook) identifica
# o paciente só pelo telefone, sem checar doctor_id -- com dois médicos
# compartilhando o mesmo paciente, pode cancelar a consulta do médico errado.
# O WhatsApp real ainda não está integrado (provider = mock), então a rota não
# serve ninguém hoje. Religar só depois do escopo por médico (doctor_id em
# patients) estar resolvido.
# app.include_router(webhooks.router, prefix=settings.api_prefix)
app.include_router(tasks.router, prefix=settings.api_prefix)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.message, "code": exc.code})


@app.exception_handler(HTTPException)
async def http_error_handler(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "Erro inesperado"
    return JSONResponse(status_code=exc.status_code, content={"success": False, "error": detail, "code": "http_error"})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    safe_details = jsonable_encoder(exc.errors())
    return JSONResponse(status_code=422, content={"success": False, "error": "Dados inválidos", "code": "validation_error", "details": safe_details})


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("unexpected_error", exc_info=exc)
    return JSONResponse(status_code=500, content={"success": False, "error": "Erro interno", "code": "internal_error"})


@app.get("/health")
async def health_check() -> dict[str, object]:
    return {"success": True, "status": "ok"}


@app.get("/ready")
async def ready_check() -> dict[str, object]:
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    return {"success": True, "status": "ready"}
