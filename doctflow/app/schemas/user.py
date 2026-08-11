from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.common import UserRole, normalize_br_phone


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=10, max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_br_phone(value)


class UserCreate(UserBase):
    role: UserRole = UserRole.patient
    is_active: bool = True


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    role: UserRole
    full_name: str
    phone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuthLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=255)


class AuthRefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload da tela "definir nova senha".

    O frontend recebe do link do e-mail um `access_token` (fragmento da URL) ou
    um `token_hash` (query string) e repassa aqui junto da nova senha.
    """

    new_password: str = Field(min_length=8, max_length=255)
    access_token: str | None = None
    token_hash: str | None = None
    # O Supabase inclui `type` na URL do link (recovery | invite | email_change).
    # Só é usado quando token_hash precisa ser verificado; com access_token é ignorado.
    type: str = "recovery"

    @model_validator(mode="after")
    def require_token(self) -> "ResetPasswordRequest":
        if not self.access_token and not self.token_hash:
            raise ValueError("Informe access_token ou token_hash do link de recuperação")
        return self


class ResetPasswordResponse(BaseModel):
    success: bool = True
    message: str = "Senha redefinida com sucesso. Faça login com a nova senha."


class DoctorRegisterRequest(UserBase):
    specialty: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=120)
    bio: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=500)


class TokenPairResponse(BaseModel):
    token_type: str = "bearer"
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserRead


class ForgotPasswordResponse(BaseModel):
    success: bool = True
    message: str = "Se o e-mail existir, as instruções foram enviadas."


class MeResponse(BaseModel):
    user: UserRead
