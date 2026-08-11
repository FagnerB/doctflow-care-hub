from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.exceptions import NotFoundError, ValidationError
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, weekday_key
from app.models.doctor import Doctor
from app.models.schedule import ScheduleException
from app.schemas.doctor import DoctorConfig
from app.schemas.schedule import AvailabilitySlot


CANCELLED_STATUSES = {
    AppointmentStatus.cancelled_by_patient,
    AppointmentStatus.cancelled_by_doctor,
}


@dataclass(slots=True)
class SlotWindow:
    start: datetime
    end: datetime


async def fetch_doctor_schedule_context(
    session: AsyncSession,
    doctor_id: str,
    target_date: date,
) -> tuple[Doctor, list[Appointment], list[ScheduleException]]:
    doctor = await session.scalar(select(Doctor).where(Doctor.id == doctor_id))
    if doctor is None:
        raise NotFoundError("Médico não encontrado")

    local_timezone = ZoneInfo(settings.timezone)
    appointments_result = await session.scalars(
        select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.scheduled_at >= datetime.combine(target_date, time.min, tzinfo=local_timezone),
            Appointment.scheduled_at < datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=local_timezone),
            Appointment.status.notin_(CANCELLED_STATUSES),
        )
    )
    appointments = list(appointments_result.all())

    exceptions_result = await session.scalars(
        select(ScheduleException).where(ScheduleException.doctor_id == doctor_id, ScheduleException.exception_date == target_date)
    )
    exceptions = list(exceptions_result.all())
    return doctor, appointments, exceptions


def _parse_config(doctor: Doctor) -> DoctorConfig:
    config = doctor.config_json or {}
    if isinstance(config, DoctorConfig):
        return config
    return DoctorConfig.model_validate(config)


def _day_windows(config: DoctorConfig, target_date: date) -> list[SlotWindow]:
    local_tz = ZoneInfo(settings.timezone)
    day_name = weekday_key(target_date)
    windows: list[SlotWindow] = []
    for window in config.working_hours.get(day_name, []):
        start_hour, start_minute = map(int, window.start.split(":"))
        end_hour, end_minute = map(int, window.end.split(":"))
        windows.append(
            SlotWindow(
                start=datetime.combine(target_date, time(start_hour, start_minute), tzinfo=local_tz),
                end=datetime.combine(target_date, time(end_hour, end_minute), tzinfo=local_tz),
            )
        )
    return windows


def _exception_windows(exceptions: list[ScheduleException], target_date: date) -> list[SlotWindow]:
    local_tz = ZoneInfo(settings.timezone)
    windows: list[SlotWindow] = []
    for exception in exceptions:
        if exception.start_time is None or exception.end_time is None:
            # Bloqueio de dia inteiro: cobre até o início do dia seguinte para não
            # deixar escapar um slot que termine às 23:59:59.
            windows.append(
                SlotWindow(
                    start=datetime.combine(target_date, time.min, tzinfo=local_tz),
                    end=datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=local_tz),
                )
            )
            continue
        windows.append(
            SlotWindow(
                start=datetime.combine(target_date, exception.start_time, tzinfo=local_tz),
                end=datetime.combine(target_date, exception.end_time, tzinfo=local_tz),
            )
        )
    return windows


def _overlaps(window: SlotWindow, start: datetime, end: datetime) -> bool:
    return start < window.end and end > window.start


def generate_available_slots(
    doctor: Doctor,
    target_date: date,
    appointments: list[Appointment],
    exceptions: list[ScheduleException],
    now: datetime | None = None,
) -> list[AvailabilitySlot]:
    config = _parse_config(doctor)
    # Não use o nome `timezone` aqui: ele sombrearia datetime.timezone e quebraria
    # `timezone.utc` logo abaixo, ao normalizar datas naive vindas do banco.
    local_tz = ZoneInfo(settings.timezone)
    current_time = now.astimezone(local_tz) if now is not None else datetime.now(local_tz)
    booking_deadline = current_time.date() + timedelta(days=config.advance_booking_days)

    if target_date < current_time.date() or target_date > booking_deadline:
        return []

    duration = timedelta(minutes=config.consultation_duration_minutes)
    windows = _day_windows(config, target_date)
    if not windows:
        return []

    exception_windows = _exception_windows(exceptions, target_date)
    occupied_windows = []
    for appointment in appointments:
        scheduled_at = appointment.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        start_local = scheduled_at.astimezone(local_tz)
        occupied_windows.append(
            SlotWindow(start=start_local, end=start_local + timedelta(minutes=appointment.duration_minutes))
        )

    slots: list[AvailabilitySlot] = []
    for working_window in windows:
        slot_start = working_window.start
        while slot_start + duration <= working_window.end:
            slot_end = slot_start + duration
            is_available = slot_start >= current_time
            if is_available:
                for exception_window in exception_windows:
                    if _overlaps(exception_window, slot_start, slot_end):
                        is_available = False
                        break
            if is_available:
                for occupied_window in occupied_windows:
                    if _overlaps(occupied_window, slot_start, slot_end):
                        is_available = False
                        break
            slots.append(AvailabilitySlot(start_time=slot_start, end_time=slot_end, is_available=is_available))
            slot_start = slot_end

    return [slot for slot in slots if slot.is_available]


def desired_datetime_to_local(desired_datetime: datetime) -> datetime:
    local_tz = ZoneInfo(settings.timezone)
    if desired_datetime.tzinfo is None:
        return desired_datetime.replace(tzinfo=local_tz)
    return desired_datetime.astimezone(local_tz)


def desired_datetime_to_utc(desired_datetime: datetime) -> datetime:
    return desired_datetime_to_local(desired_datetime).astimezone(timezone.utc)


def validate_booking_window(doctor: Doctor, desired_datetime: datetime) -> None:
    """Valida a data pedida contra o passado e a janela de agendamento.

    Levanta ValidationError (400). Antes era ValueError, que escapava para o
    handler genérico e devolvia 500 ao paciente.
    """
    config = _parse_config(doctor)
    local_datetime = desired_datetime_to_local(desired_datetime)
    now = datetime.now(ZoneInfo(settings.timezone))
    if local_datetime < now:
        raise ValidationError("O horário escolhido está no passado")
    if local_datetime.date() > now.date() + timedelta(days=config.advance_booking_days):
        raise ValidationError(
            f"Este médico aceita agendamentos com no máximo {config.advance_booking_days} dias de antecedência"
        )
