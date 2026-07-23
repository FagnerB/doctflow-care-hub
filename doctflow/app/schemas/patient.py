from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.common import normalize_br_phone


class PatientBase(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=10, max_length=20)
    email: EmailStr | None = None
    cpf: str | None = Field(default=None, max_length=20)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_br_phone(value)


class PatientCreate(PatientBase):
    pass


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    phone: str
    email: EmailStr | None
    cpf: str | None
    created_at: datetime


class PatientListResponse(BaseModel):
    items: list[PatientRead]
    total: int
