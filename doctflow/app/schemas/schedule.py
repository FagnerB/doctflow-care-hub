from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, model_validator


class WorkingHourWindow(BaseModel):
    start: time
    end: time


class ScheduleExceptionCreate(BaseModel):
    """Bloqueio de agenda.

    Sem `start_time`/`end_time` o dia inteiro é bloqueado (férias, feriado).
    Com ambos, bloqueia apenas a faixa informada.
    """

    exception_date: date
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_window(self) -> "ScheduleExceptionCreate":
        if (self.start_time is None) != (self.end_time is None):
            raise ValueError("Informe start_time e end_time juntos, ou nenhum dos dois para bloquear o dia inteiro")
        if self.start_time is not None and self.end_time is not None and self.start_time >= self.end_time:
            raise ValueError("start_time deve ser anterior a end_time")
        return self


class ScheduleExceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    doctor_id: str
    exception_date: date
    start_time: time | None
    end_time: time | None
    reason: str | None
    created_at: datetime


class AvailabilitySlot(BaseModel):
    start_time: datetime
    end_time: datetime
    is_available: bool = True


class AvailabilityResponse(BaseModel):
    doctor_slug: str
    date: date
    slots: list[AvailabilitySlot]


class UpcomingAppointmentSummary(BaseModel):
    id: str
    patient_name: str
    patient_phone: str
    scheduled_at: datetime
    duration_minutes: int
    status: str


class DoctorStatsResponse(BaseModel):
    """Números do dashboard do médico para um mês de referência."""

    month: str
    total_appointments: int
    confirmed: int
    completed: int
    no_show: int
    cancelled: int
    attendance_rate: float
    upcoming: list[UpcomingAppointmentSummary]
