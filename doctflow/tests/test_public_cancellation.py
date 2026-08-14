"""POST /appointments/{id}/cancel -- cancelamento público via link (P2.4).

O único caminho antes disso era responder CANCELAR no WhatsApp, que está
desligado (ver app/main.py). Sem esta rota, nenhum paciente conseguia
se autocancelar.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config import settings
from app.models.appointment import Appointment
from app.models.common import AppointmentStatus
from app.models.patient import Patient

LOCAL_TZ = ZoneInfo(settings.timezone)


async def _criar_consulta(
    session, doctor, *, horas_a_frente: float, status: AppointmentStatus = AppointmentStatus.confirmed
) -> Appointment:
    patient = Patient(name="Paciente Teste", phone="+5511900001111")
    session.add(patient)
    await session.flush()

    appointment = Appointment(
        id="appt-cancel-1",
        doctor_id=doctor.id,
        patient_id=patient.id,
        scheduled_at=datetime.now(LOCAL_TZ) + timedelta(hours=horas_a_frente),
        duration_minutes=30,
        status=status,
    )
    session.add(appointment)
    await session.commit()
    return appointment


async def test_cancela_consulta_ativa_pelo_link(client, session, doctor) -> None:
    appointment = await _criar_consulta(session, doctor, horas_a_frente=72)

    response = await client.post(f"/api/appointments/{appointment.id}/cancel")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled_by_patient"

    await session.refresh(appointment)
    assert appointment.status == AppointmentStatus.cancelled_by_patient


async def test_respeita_prazo_minimo_de_cancelamento(session, doctor, client) -> None:
    # Fixture do doctor usa cancellation_policy_hours=24 -- 2h à frente já é tarde.
    appointment = await _criar_consulta(session, doctor, horas_a_frente=2)

    response = await client.post(f"/api/appointments/{appointment.id}/cancel")
    assert response.status_code == 403

    await session.refresh(appointment)
    assert appointment.status == AppointmentStatus.confirmed


async def test_nao_cancela_consulta_ja_cancelada(session, doctor, client) -> None:
    appointment = await _criar_consulta(
        session, doctor, horas_a_frente=72, status=AppointmentStatus.cancelled_by_patient
    )

    response = await client.post(f"/api/appointments/{appointment.id}/cancel")
    assert response.status_code == 404


async def test_cancelamento_de_id_inexistente_da_404(client) -> None:
    response = await client.post("/api/appointments/nao-existe/cancel")
    assert response.status_code == 404
