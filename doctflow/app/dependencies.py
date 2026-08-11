from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.exceptions import ForbiddenError, TooManyRequestsError, UnauthorizedError
from app.models.common import UserRole
from app.models.doctor import Doctor
from app.models.user import User
from app.services.auth_service import auth_service

bearer_scheme = HTTPBearer(auto_error=True, scheme_name="BearerAuth")

RateKey = tuple[str, str]
_rate_buckets: dict[RateKey, deque[datetime]] = defaultdict(deque)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    # Precisa repassar o generator (e não `return session`), senão o `async with`
    # de get_session() só fecha no GC e a conexão vaza — fatal no pooler do Supabase.
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> User:
    token = credentials.credentials
    payload = auth_service.decode_token(token)
    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Token sem user_id")
    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("Usuário inválido ou inativo")
    return user


def require_roles(*roles: UserRole):
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenError("Permissão insuficiente")
        return current_user

    return dependency


async def require_owner(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.owner:
        raise ForbiddenError("Acesso restrito ao owner")
    return current_user


async def get_current_doctor(session: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_user)) -> Doctor:
    if current_user.role not in {UserRole.doctor, UserRole.owner}:
        raise ForbiddenError("Acesso restrito ao médico")
    doctor = await session.scalar(select(Doctor).where(Doctor.user_id == current_user.id))
    if doctor is None:
        raise ForbiddenError("Perfil de médico não encontrado")
    return doctor


def _client_ip(request: Request) -> str:
    # Railway/Supabase colocam a app atrás de proxy: sem ler X-Forwarded-For todos
    # os clientes compartilhariam o IP do proxy e um único paciente bloquearia todos.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(limit: int = 5, window_seconds: int = 60):
    """Fábrica de rate limit por IP+rota.

    Precisa ser fábrica: se `limit`/`window_seconds` fossem parâmetros da própria
    dependência, o FastAPI os exporia como query params e qualquer um poderia
    burlar o limite chamando `?limit=99999`.
    """

    async def dependency(request: Request) -> None:
        key = (request.url.path, _client_ip(request))
        now = datetime.now(timezone.utc)
        bucket = _rate_buckets[key]
        while bucket and now - bucket[0] > timedelta(seconds=window_seconds):
            bucket.popleft()
        if len(bucket) >= limit:
            raise TooManyRequestsError("Muitas requisições. Tente novamente em instantes.")
        bucket.append(now)

    return dependency


# Escrita pública (criar agendamento): restritivo.
rate_limit_public = rate_limit(limit=5, window_seconds=60)
# Leitura pública (perfil e disponibilidade): o paciente navega vários dias
# seguidos no calendário, então 5/min bloquearia uso legítimo.
rate_limit_public_generous = rate_limit(limit=60, window_seconds=60)
# Webhook do provedor de WhatsApp: tolerante a rajadas, mas com teto.
rate_limit_webhook = rate_limit(limit=30, window_seconds=60)
# Endpoints sensíveis de autenticação (recuperar/redefinir senha): freia
# tentativa de força bruta e abuso do disparo de e-mails.
rate_limit_auth = rate_limit(limit=5, window_seconds=300)
