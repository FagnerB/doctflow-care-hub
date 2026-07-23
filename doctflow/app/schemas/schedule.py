from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class WorkingHourWindow(BaseModel):
    start: time
    end: time


class ScheduleExceptionCreate(BaseModel):
    exception_date: date
    start_time: time | None = None
    end_time: time | None = None
    reason: str | None = Field(default=None, max_length=1000)


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
