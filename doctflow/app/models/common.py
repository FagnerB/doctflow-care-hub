from __future__ import annotations

import unicodedata
from datetime import date, datetime, time, timezone
from enum import Enum
from zoneinfo import ZoneInfo


class StrEnum(str, Enum):
    pass


class UserRole(StrEnum):
    owner = "owner"
    doctor = "doctor"
    patient = "patient"


class AppointmentStatus(StrEnum):
    pending = "pending"
    confirmed = "confirmed"
    completed = "completed"
    cancelled_by_patient = "cancelled_by_patient"
    cancelled_by_doctor = "cancelled_by_doctor"
    no_show = "no_show"


class NotificationType(StrEnum):
    confirmation = "confirmation"
    reminder_24h = "reminder_24h"
    reminder_2h = "reminder_2h"
    cancellation = "cancellation"


class NotificationStatus(StrEnum):
    sent = "sent"
    delivered = "delivered"
    failed = "failed"
    # Provider em modo mock (console): nada saiu de verdade, só foi logado.
    simulated = "simulated"


DAYS_OF_WEEK = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def default_working_hours() -> dict[str, list[dict[str, str]]]:
    return {day: [] for day in DAYS_OF_WEEK}


def default_doctor_config() -> dict[str, object]:
    return {
        "consultation_duration_minutes": 30,
        "advance_booking_days": 30,
        "auto_confirm": True,
        "cancellation_policy_hours": 24,
        "working_hours": default_working_hours(),
    }


def normalize_br_phone(phone: str) -> str:
    """Normaliza telefone brasileiro para E.164 (+55DDDNUMERO).

    Aceita fixo (10 dígitos com DDD) e celular (11 dígitos com nono dígito),
    com ou sem o prefixo de país 55 e com ou sem o "0" de operadora.
    """
    digits = "".join(character for character in phone if character.isdigit())

    # Remove o "0" de discagem interurbana (ex.: 011 99999-8888).
    if len(digits) in (11, 12) and digits.startswith("0"):
        digits = digits[1:]

    # Já veio com código do país: 55 + DDD(2) + número(8 fixo ou 9 celular).
    if len(digits) in (12, 13) and digits.startswith("55"):
        return f"+{digits}"

    # Sem código do país: DDD(2) + número(8 fixo ou 9 celular).
    if len(digits) in (10, 11):
        return f"+55{digits}"

    raise ValueError("Telefone BR inválido: informe DDD + número (ex.: 11987654321)")


def phone_digits(phone: str) -> str:
    return "".join(character for character in phone if character.isdigit())


def normalize_name(name: str) -> str:
    """Chave de identidade do paciente: minúsculas, sem acento, espaços colapsados.

    Usada em (doctor_id, phone, name_key) pra decidir se um novo agendamento
    é a mesma pessoa de um cadastro existente ou uma pessoa diferente
    compartilhando o telefone (ex.: mãe agendando pra dois filhos). Mantém
    pontuação como veio -- só normaliza o que varia por acidente de digitação
    (maiúscula, acento, espaço extra), não o que pode ser parte real do nome.
    """
    sem_acento = unicodedata.normalize("NFKD", name)
    sem_acento = "".join(character for character in sem_acento if not unicodedata.combining(character))
    return " ".join(sem_acento.lower().split())


def weekday_key(date_value: date) -> str:
    return DAYS_OF_WEEK[date_value.weekday()]


def make_timezone(name: str) -> ZoneInfo:
    return ZoneInfo(name)


def to_local_datetime(value: datetime, timezone_name: str) -> datetime:
    tz = make_timezone(timezone_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def to_utc(value: datetime, timezone_name: str) -> datetime:
    return to_local_datetime(value, timezone_name).astimezone(timezone.utc)


def time_to_minutes(value: time) -> int:
    return value.hour * 60 + value.minute
