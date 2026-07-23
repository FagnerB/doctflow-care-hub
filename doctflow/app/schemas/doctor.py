from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import default_doctor_config, normalize_br_phone
from app.schemas.user import UserRead


class TimeWindow(BaseModel):
    start: str = Field(pattern=r"^\d{2}:\d{2}$")
    end: str = Field(pattern=r"^\d{2}:\d{2}$")


class DoctorConfig(BaseModel):
    consultation_duration_minutes: int = Field(default=30, ge=5, le=240)
    advance_booking_days: int = Field(default=30, ge=0, le=365)
    auto_confirm: bool = True
    cancellation_policy_hours: int = Field(default=24, ge=0, le=168)
    working_hours: dict[str, list[TimeWindow]] = Field(default_factory=lambda: default_doctor_config()["working_hours"])


class DoctorBase(BaseModel):
    specialty: str = Field(min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_verified: bool = False
    config_json: DoctorConfig = Field(default_factory=DoctorConfig)


class DoctorCreate(DoctorBase):
    email: str
    full_name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=10, max_length=20)
    slug: str = Field(min_length=2, max_length=120)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_br_phone(value)


class DoctorUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    specialty: str | None = Field(default=None, min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=2000)
    avatar_url: str | None = Field(default=None, max_length=500)
    config_json: DoctorConfig | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_br_phone(value)


class DoctorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    specialty: str
    bio: str | None
    avatar_url: str | None
    is_verified: bool
    config_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    user: UserRead


class DoctorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    full_name: str
    specialty: str
    bio: str | None
    avatar_url: str | None
    is_verified: bool
    config_json: dict[str, Any]


class DoctorListResponse(BaseModel):
    items: list[DoctorRead]
    total: int
