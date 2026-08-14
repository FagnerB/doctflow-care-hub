"""Lembretes automáticos de 24h e 2h."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.config import settings
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus, NotificationType
from app.models.notification_log import NotificationLog
from app.models.patient import Patient
from app.services.appointment_service import appointment_service


async def _criar_consulta(
    session,
    doctor,
    *,
    horas_a_frente: float,
    status: AppointmentStatus = AppointmentStatus.confirmed,
    appointment_id: str = "appt-1",
    phone: str = "+5511912345678",
) -> Appointment:
    patient = await session.scalar(select(Patient).where(Patient.phone == phone))
    if patient is None:
        patient = Patient(name="Carlos Souza", phone=phone)
        session.add(patient)
        await session.flush()

    appointment = Appointment(
        id=appointment_id,
        doctor_id=doctor.id,
        patient_id=patient.id,
        scheduled_at=datetime.now(timezone.utc) + timedelta(hours=horas_a_frente),
        duration_minutes=30,
        status=status,
    )
    session.add(appointment)
    await session.commit()
    return appointment


async def test_envia_lembrete_24h(session, doctor) -> None:
    await _criar_consulta(session, doctor, horas_a_frente=24.2)

    sent, failed = await appointment_service.run_reminders(session)
    await session.commit()

    assert (sent, failed) == (1, 0)
    logs = (await session.scalars(select(NotificationLog))).all()
    assert [log.type for log in logs] == [NotificationType.reminder_24h]


async def test_envia_lembrete_2h(session, doctor) -> None:
    await _criar_consulta(session, doctor, horas_a_frente=2.2)

    sent, _ = await appointment_service.run_reminders(session)
    await session.commit()

    assert sent == 1
    logs = (await session.scalars(select(NotificationLog))).all()
    assert [log.type for log in logs] == [NotificationType.reminder_2h]


async def test_nao_duplica_lembrete_em_execucoes_seguidas(session, doctor) -> None:
    """O job roda de hora em hora; a idempotência vem do notification_logs."""
    await _criar_consulta(session, doctor, horas_a_frente=24.2)

    primeira, _ = await appointment_service.run_reminders(session)
    await session.commit()
    segunda, _ = await appointment_service.run_reminders(session)
    await session.commit()

    assert primeira == 1
    assert segunda == 0
    logs = (await session.scalars(select(NotificationLog))).all()
    assert len(logs) == 1


async def test_ignora_consulta_fora_da_janela(session, doctor) -> None:
    await _criar_consulta(session, doctor, horas_a_frente=72)

    sent, failed = await appointment_service.run_reminders(session)
    await session.commit()

    assert (sent, failed) == (0, 0)
    assert (await session.scalars(select(NotificationLog))).all() == []


async def test_ignora_consulta_cancelada(session, doctor) -> None:
    await _criar_consulta(
        session, doctor, horas_a_frente=24.2, status=AppointmentStatus.cancelled_by_patient
    )

    sent, _ = await appointment_service.run_reminders(session)
    await session.commit()

    assert sent == 0


async def test_reminder_sent_at_fica_nulo_em_modo_mock(session, doctor) -> None:
    """Provider console (mock) não entrega nada de verdade -- reminder_sent_at
    só pode ser preenchido quando o envio for real, senão mente pro paciente."""
    appointment = await _criar_consulta(session, doctor, horas_a_frente=2.2)
    assert appointment.reminder_sent_at is None

    sent, _ = await appointment_service.run_reminders(session)
    await session.commit()
    await session.refresh(appointment)

    assert sent == 1
    assert appointment.reminder_sent_at is None

    logs = (await session.scalars(select(NotificationLog))).all()
    assert logs[0].status.value == "simulated"


async def test_janela_cobre_o_intervalo_do_scheduler() -> None:
    """Se a janela for menor que o intervalo, consultas caem entre duas execuções."""
    assert settings.reminders_window_minutes >= settings.reminders_interval_minutes


# --------------------------------------------------------------------------
# Endpoint de cron
# --------------------------------------------------------------------------


async def test_cron_desabilitado_sem_secret(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "cron_secret", "")
    response = await client.post("/api/tasks/reminders/run")
    assert response.status_code == 403


async def test_cron_rejeita_secret_invalido(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "cron_secret", "segredo-cron")
    response = await client.post("/api/tasks/reminders/run", headers={"X-Cron-Secret": "errado"})
    assert response.status_code == 403


async def test_cron_aceita_secret_valido(client, session, doctor, session_factory, monkeypatch) -> None:
    monkeypatch.setattr(settings, "cron_secret", "segredo-cron")
    # O job abre sessão própria (roda fora do ciclo de request), então precisa
    # apontar para o banco de teste.
    monkeypatch.setattr("app.tasks.reminder_jobs.AsyncSessionLocal", session_factory)

    await _criar_consulta(session, doctor, horas_a_frente=24.2)

    response = await client.post("/api/tasks/reminders/run", headers={"X-Cron-Secret": "segredo-cron"})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["sent"] == 1
