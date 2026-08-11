from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.models.common import UserRole, normalize_br_phone
from app.models.doctor import Doctor
from app.models.user import User
from app.services.email_service import email_service


class SupabaseIntegrationError(UnauthorizedError):
    pass


class AuthService:
    def __init__(self) -> None:
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm

    def create_access_token(self, user: User) -> tuple[str, int]:
        expires = timedelta(minutes=settings.access_token_expire_minutes)
        expire_at = datetime.now(timezone.utc) + expires
        payload = {
            "sub": user.id,
            "user_id": user.id,
            "role": user.role.value,
            "exp": expire_at,
            "iat": datetime.now(timezone.utc),
            "token_type": "access",
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, int(expires.total_seconds())

    def create_refresh_token(self, user: User) -> str:
        expires = timedelta(days=settings.refresh_token_expire_days)
        expire_at = datetime.now(timezone.utc) + expires
        payload = {
            "sub": user.id,
            "user_id": user.id,
            "role": user.role.value,
            "exp": expire_at,
            "iat": datetime.now(timezone.utc),
            "token_type": "refresh",
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except JWTError as exc:
            raise UnauthorizedError("Token inválido") from exc

    def decode_refresh_token(self, token: str) -> dict[str, Any]:
        payload = self.decode_token(token)
        if payload.get("token_type") != "refresh":
            raise UnauthorizedError("Token de refresh inválido")
        return payload

    async def login_with_supabase(self, email: str, password: str) -> dict[str, Any]:
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise SupabaseIntegrationError("Supabase não configurado")

        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=password"
        headers = {"apikey": settings.supabase_anon_key, "Content-Type": "application/json"}
        payload = {"email": email, "password": password}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
        if not response.is_success:
            raise UnauthorizedError("Credenciais inválidas")
        return response.json()

    async def refresh_supabase(self, refresh_token: str) -> dict[str, Any]:
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise SupabaseIntegrationError("Supabase não configurado")

        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/token?grant_type=refresh_token"
        headers = {"apikey": settings.supabase_anon_key, "Content-Type": "application/json"}
        payload = {"refresh_token": refresh_token}
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
        if not response.is_success:
            raise UnauthorizedError("Refresh token inválido")
        return response.json()

    async def forgot_password(self, email: str) -> None:
        """Solicita o e-mail de recuperação de senha.

        Não propaga erro: a resposta ao cliente é sempre genérica para que não
        seja possível descobrir quais e-mails têm conta (enumeração de usuários).
        Falhas reais ficam registradas no log pelo EmailService.
        """
        await email_service.send_password_recovery(email)

    async def reset_password(
        self,
        new_password: str,
        *,
        access_token: str | None = None,
        token_hash: str | None = None,
        verify_type: str = "recovery",
    ) -> None:
        """Efetiva a nova senha no Supabase Auth.

        Aceita os dois formatos que o link do e-mail pode entregar ao frontend:
        - `access_token`: token de recuperação já presente no fragmento da URL;
        - `token_hash`: precisa ser trocado por um access_token via /verify.

        `verify_type` precisa bater com o tipo real do token — o link de
        primeiro acesso (convite) chega como `type=invite`, o de "esqueci minha
        senha" como `type=recovery`. O Supabase rejeita a verificação se o tipo
        não corresponder ao que foi usado para gerar o token.
        """
        if not settings.supabase_url or not settings.supabase_anon_key:
            raise SupabaseIntegrationError("Supabase não configurado")

        if not access_token and not token_hash:
            raise UnauthorizedError("Token de recuperação ausente")

        base_url = settings.supabase_url.rstrip("/")
        headers = {"apikey": settings.supabase_anon_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30) as client:
            if not access_token:
                verify_response = await client.post(
                    f"{base_url}/auth/v1/verify",
                    headers=headers,
                    json={"type": verify_type, "token_hash": token_hash},
                )
                if not verify_response.is_success:
                    raise UnauthorizedError("Link de recuperação inválido ou expirado")
                access_token = verify_response.json().get("access_token")
                if not access_token:
                    raise UnauthorizedError("Link de recuperação inválido ou expirado")

            update_response = await client.put(
                f"{base_url}/auth/v1/user",
                headers={**headers, "Authorization": f"Bearer {access_token}"},
                json={"password": new_password},
            )

        if not update_response.is_success:
            raise UnauthorizedError("Não foi possível redefinir a senha. Solicite um novo link.")

    async def create_supabase_user(self, email: str, full_name: str, phone: str, role: UserRole) -> str:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            return str(uuid4())

        url = f"{settings.supabase_url.rstrip('/')}/auth/v1/admin/users"
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "email": email,
            "email_confirm": True,
            "user_metadata": {"full_name": full_name, "phone": phone, "role": role.value},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=payload)
        if not response.is_success:
            raise ConflictError("Não foi possível criar usuário no Supabase")
        data = response.json()
        return data.get("id") or data.get("user", {}).get("id") or str(uuid4())

    async def upsert_user_profile(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        email: str,
        full_name: str,
        phone: str,
        role: UserRole,
        is_active: bool = True,
    ) -> User:
        normalized_phone = normalize_br_phone(phone)
        user = await session.get(User, user_id)
        if user is None:
            existing_by_email = await session.scalar(select(User).where(User.email == email))
            if existing_by_email is not None:
                user = existing_by_email
            else:
                user = User(id=user_id, email=email, full_name=full_name, phone=normalized_phone, role=role, is_active=is_active)
                session.add(user)
                await session.flush()
                return user

        user.email = email
        user.full_name = full_name
        user.phone = normalized_phone
        user.role = role
        user.is_active = is_active
        await session.flush()
        return user

    async def get_user_by_email(self, session: AsyncSession, email: str) -> User:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return user

    async def get_user_by_id(self, session: AsyncSession, user_id: str) -> User:
        user = await session.get(User, user_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado")
        return user

    async def ensure_doctor_profile(
        self,
        session: AsyncSession,
        *,
        user: User,
        slug: str,
        specialty: str,
        bio: str | None = None,
        avatar_url: str | None = None,
        is_verified: bool = False,
        config_json: dict[str, Any] | None = None,
    ) -> Doctor:
        doctor = await session.scalar(select(Doctor).where(Doctor.user_id == user.id))
        if doctor is None:
            if await session.scalar(select(Doctor).where(Doctor.slug == slug)) is not None:
                raise ConflictError("Slug de médico já existe")
            doctor = Doctor(
                user_id=user.id,
                slug=slug,
                specialty=specialty,
                bio=bio,
                avatar_url=avatar_url,
                is_verified=is_verified,
                config_json=config_json or {},
            )
            session.add(doctor)
            await session.flush()
            return doctor

        if slug != doctor.slug and await session.scalar(select(Doctor).where(Doctor.slug == slug)) is not None:
            raise ConflictError("Slug de médico já existe")
        doctor.slug = slug
        doctor.specialty = specialty
        doctor.bio = bio
        doctor.avatar_url = avatar_url
        doctor.is_verified = is_verified
        if config_json is not None:
            doctor.config_json = config_json
        await session.flush()
        return doctor


auth_service = AuthService()
