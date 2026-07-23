from __future__ import annotations

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus
from app.models.doctor import Doctor
from app.models.schedule import ScheduleException
from app.services.schedule_service import generate_available_slots


def test_generate_available_slots_removes_busy_and_blocked_windows() -> None:
    doctor = Doctor(
        id="doctor-1",
        user_id="user-1",
        slug="dr-silva",
        specialty="Cardiologia",
        config_json={
            "consultation_duration_minutes": 30,
            "advance_booking_days": 30,
            "auto_confirm": True,
            "cancellation_policy_hours": 24,
            "working_hours": {
                "monday": [
                    {"start": "08:00", "end": "10:00"},
                ],
                "tuesday": [],
                "wednesday": [],
                "thursday": [],
                "friday": [],
                "saturday": [],
                "sunday": [],
            },
        },
    )

    tz = ZoneInfo(settings.timezone)
    target_date = date(2026, 7, 27)
    appointments = [
        Appointment(
            id="appointment-1",
            doctor_id=doctor.id,
            patient_id="patient-1",
            scheduled_at=datetime(2026, 7, 27, 8, 30, tzinfo=tz),
            duration_minutes=30,
            status=AppointmentStatus.confirmed,
        )
    ]
    exceptions = [
        ScheduleException(
            id="exception-1",
            doctor_id=doctor.id,
            exception_date=target_date,
            start_time=time(9, 0),
            end_time=time(9, 30),
            reason="Bloqueio",
        )
    ]

    slots = generate_available_slots(
        doctor=doctor,
        target_date=target_date,
        appointments=appointments,
        exceptions=exceptions,
        now=datetime(2026, 7, 27, 7, 0, tzinfo=tz),
    )

    assert [(slot.start_time.time(), slot.end_time.time()) for slot in slots] == [
        (time(8, 0), time(8, 30)),
        (time(9, 30), time(10, 0)),
    ]
