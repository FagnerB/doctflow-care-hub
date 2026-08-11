from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.common import AppointmentStatus, normalize_br_phone
from app.schemas.patient import PatientRead


class AppointmentCreatePublic(BaseModel):
    doctor_slug: str = Field(min_length=2, max_length=120)
    patient_name: str = Field(min_length=2, max_length=255)
    patient_phone: str = Field(min_length=10, max_length=20)
    patient_email: str | None = None
    patient_cpf: str | None = Field(default=None, max_length=20)
    desired_datetime: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("patient_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_br_phone(value)


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    patient_id: str
    scheduled_at: datetime
    duration_minutes: int
    status: AppointmentStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime
    confirmation_sent_at: datetime | None
    reminder_sent_at: datetime | None
    patient: PatientRead | None = None


class AppointmentPublicStatusResponse(BaseModel):
    # Sem from_attributes o endpoint de status quebrava com 500 ao validar o
    # objeto ORM vindo do banco.
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: AppointmentStatus
    scheduled_at: datetime
    duration_minutes: int
    confirmation_sent_at: datetime | None = None
    reminder_sent_at: datetime | None = None


class AppointmentWebhookPayload(BaseModel):
    from_phone: str
    message: str

    @field_validator("from_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_br_phone(value)


class WebhookAckResponse(BaseModel):
    success: bool = True
    cancelled: bool = False
    message: str = "Mensagem recebida."


class ReminderRunResponse(BaseModel):
    success: bool = True
    sent: int = 0
    failed: int = 0
    message: str = "Processamento concluído."
