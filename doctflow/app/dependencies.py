from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Callable, Coroutine, TypeVar

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.exceptions import ForbiddenError, TooManyRequestsError, UnauthorizedError
from app.models.common import UserRole
from app.models.doctor import Doctor
from app.models.user import User
from app.services.auth_service import auth_service

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

RateKey = tuple[str, str]
_rate_buckets: dict[RateKey, deque[datetime]] = defaultdict(deque)


async def get_db_session() -> AsyncSession:
    async for session in get_session():
        return session
    raise RuntimeError("Sessão de banco indisponível")


async def get_current_user(session: AsyncSession = Depends(get_db_session), token: str = Depends(oauth2_scheme)) -> User:
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


async def rate_limit_public(request: Request, limit: int = 5, window_seconds: int = 60) -> None:
    ip = request.client.host if request.client else "unknown"
    key = (request.url.path, ip)
    now = datetime.now(timezone.utc)
    bucket = _rate_buckets[key]
    while bucket and now - bucket[0] > timedelta(seconds=window_seconds):
        bucket.popleft()
    if len(bucket) >= limit:
        raise TooManyRequestsError("Muitas requisições. Tente novamente em instantes.")
    bucket.append(now)
