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
    desired_datetime: datetime
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("patient_phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        return normalize_br_phone(value)


class AppointmentCreateByDoctor(BaseModel):
    """Agendamento manual feito pelo próprio médico (telefone, balcão, encaixe).

    Diferente de AppointmentCreatePublic: não valida contra o expediente
    configurado nem a janela de antecedência — o profissional pode encaixar
    fora do horário normal. Só o conflito real de horário é bloqueado (mesma
    constraint única do banco usada no fluxo público).
    """

    patient_name: str = Field(min_length=2, max_length=255)
    patient_phone: str = Field(min_length=10, max_length=20)
    patient_email: str | None = None
    scheduled_at: datetime
    notes: str | None = Field(default=None, max_length=2000)
    # Padrão True (avisar é o caso comum). Precisa poder ser False para
    # importar a agenda já existente do consultório sem disparar confirmação
    # retroativa para pacientes que já sabem da própria consulta.
    notify_patient: bool = True

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
    """Status público da consulta — o id (UUID) funciona como token de acesso.

    Inclui nome do médico e dados do paciente porque essa é a única tela que
    o paciente vê depois de agendar; sem eles a página fica sem contexto
    (`/appointment/{id}` não sabe dizer "consulta com quem" nem "de quem").
    Seguro no mesmo modelo do restante do link: só quem tem o UUID (recebido
    na confirmação) chega a essa informação, igual já vale para
    confirmation_sent_at/reminder_sent_at.
    """

    id: str
    status: AppointmentStatus
    scheduled_at: datetime
    duration_minutes: int
    confirmation_sent_at: datetime | None = None
    reminder_sent_at: datetime | None = None
    doctor_full_name: str
    patient_name: str
    patient_phone: str


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
