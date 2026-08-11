"""Fixtures compartilhadas dos testes.

Os testes rodam contra SQLite em arquivo temporário: o objetivo é validar
regras de negócio e contratos HTTP, não o dialeto do Postgres.
"""

from __future__ import annotations

import os
from pathlib import Path

# Precisa ser definido ANTES de importar app.config (settings é cacheado no import).
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("TIMEZONE", "America/Sao_Paulo")
os.environ.setdefault("REMINDERS_SCHEDULER_ENABLED", "false")
os.environ.setdefault("WHATSAPP_PROVIDER", "console")
os.environ.setdefault("WHATSAPP_API_KEY", "")
os.environ.setdefault("SUPABASE_URL", "")
os.environ.setdefault("SUPABASE_ANON_KEY", "")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

import app.models  # noqa: F401,E402  (garante o registro de todas as tabelas)
from app.database import Base  # noqa: E402
from app.dependencies import get_db_session  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models.common import UserRole  # noqa: E402
from app.models.doctor import Doctor  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.auth_service import auth_service  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limit():
    """Os buckets de rate limit são de processo; sem limpar, um teste derruba o seguinte."""
    from app.dependencies import _rate_buckets

    _rate_buckets.clear()
    yield
    _rate_buckets.clear()


@pytest_asyncio.fixture
async def engine(tmp_path: Path):
    url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    test_engine = create_async_engine(url)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def session(session_factory):
    async with session_factory() as db_session:
        yield db_session


@pytest_asyncio.fixture
async def client(session_factory):
    """Cliente HTTP com o banco de testes injetado na dependência da app."""

    async def override_get_db_session():
        async with session_factory() as db_session:
            yield db_session

    fastapi_app.dependency_overrides[get_db_session] = override_get_db_session
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    fastapi_app.dependency_overrides.clear()


def _working_hours_all_week(start: str = "08:00", end: str = "12:00") -> dict[str, list[dict[str, str]]]:
    dias = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
    return {dia: [{"start": start, "end": end}] for dia in dias}


@pytest_asyncio.fixture
async def doctor(session) -> Doctor:
    """Médico com agenda 08:00–12:00 todos os dias e consultas de 30 min."""
    user = User(
        id="user-doctor-1",
        email="dr.silva@example.com",
        role=UserRole.doctor,
        full_name="Ana Silva",
        phone="+5511988887777",
    )
    session.add(user)
    await session.flush()

    doctor_row = Doctor(
        id="doctor-1",
        user_id=user.id,
        slug="dr-silva",
        specialty="Cardiologia",
        bio="Atendimento humanizado",
        config_json={
            "consultation_duration_minutes": 30,
            "advance_booking_days": 30,
            "auto_confirm": True,
            "cancellation_policy_hours": 24,
            "working_hours": _working_hours_all_week(),
        },
    )
    session.add(doctor_row)
    await session.commit()
    return doctor_row


@pytest.fixture
def doctor_token(doctor) -> str:
    """Bearer token válido para o médico da fixture."""

    class _User:
        id = "user-doctor-1"
        role = UserRole.doctor

    token, _ = auth_service.create_access_token(_User())  # type: ignore[arg-type]
    return token
