from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
