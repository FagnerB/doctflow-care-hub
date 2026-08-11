from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_current_user, get_db_session, rate_limit_auth, require_owner
from app.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.models.common import UserRole
from app.models.doctor import Doctor
from app.models.user import User
from app.schemas.doctor import DoctorRead
from app.schemas.user import (
    AuthLoginRequest,
    AuthRefreshRequest,
    DoctorRegisterRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MeResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenPairResponse,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=DoctorRead)
async def register_doctor(
    payload: DoctorRegisterRequest,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(require_owner),
) -> DoctorRead:
    if await session.scalar(select(User).where(User.email == payload.email)) is not None:
        raise ConflictError("Usuário já existe")
    if await session.scalar(select(User).where(User.phone == payload.phone)) is not None:
        raise ConflictError("Telefone já cadastrado")

    supabase_user_id = await auth_service.create_supabase_user(payload.email, payload.full_name, payload.phone, UserRole.doctor)
    user = await auth_service.upsert_user_profile(
        session,
        user_id=supabase_user_id,
        email=payload.email,
        full_name=payload.full_name,
        phone=payload.phone,
        role=UserRole.doctor,
    )
    doctor = await auth_service.ensure_doctor_profile(
        session,
        user=user,
        slug=payload.slug,
        specialty=payload.specialty,
        bio=payload.bio,
        avatar_url=payload.avatar_url,
        config_json=None,
    )
    await session.commit()

    doctor_result = await session.scalar(
        select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor.id)
    )
    return DoctorRead.model_validate(doctor_result)


@router.post("/login", response_model=TokenPairResponse)
async def login(payload: AuthLoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPairResponse:
    await auth_service.login_with_supabase(payload.email, payload.password)
    user = await session.scalar(select(User).where(User.email == payload.email))
    if user is None:
        raise NotFoundError("Perfil local não encontrado. Solicite o cadastro ao owner.")
    access_token, expires_in = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in, user=user)


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh_tokens(payload: AuthRefreshRequest, session: AsyncSession = Depends(get_db_session)) -> TokenPairResponse:
    token_data = auth_service.decode_refresh_token(payload.refresh_token)
    user_id = token_data.get("user_id")
    user = await session.get(User, user_id)
    if user is None:
        raise UnauthorizedError("Refresh token inválido")
    access_token, expires_in = auth_service.create_access_token(user)
    refresh_token = auth_service.create_refresh_token(user)
    return TokenPairResponse(access_token=access_token, refresh_token=refresh_token, expires_in=expires_in, user=user)


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def forgot_password(payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
    """Envia o e-mail com o link de redefinição de senha.

    Responde sempre 200 com a mesma mensagem, exista ou não a conta — assim o
    endpoint não vira um oráculo para descobrir e-mails cadastrados.
    """
    await auth_service.forgot_password(payload.email)
    return ForgotPasswordResponse()


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    dependencies=[Depends(rate_limit_auth)],
)
async def reset_password(payload: ResetPasswordRequest) -> ResetPasswordResponse:
    """Define a nova senha a partir do token recebido no e-mail de recuperação."""
    await auth_service.reset_password(
        payload.new_password,
        access_token=payload.access_token,
        token_hash=payload.token_hash,
        verify_type=payload.type,
    )
    return ResetPasswordResponse()


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(user=current_user)
