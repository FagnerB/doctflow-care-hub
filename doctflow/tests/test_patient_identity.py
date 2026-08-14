"""Identidade de paciente: (doctor_id, telefone, nome normalizado).

Paciente era global antes desta rodada -- phone tinha unique=True sem
doctor_id. Isso causava dois problemas reais: dois médicos podiam acabar
compartilhando o mesmo registro (nome/e-mail sobrescritos por quem
agendasse por último), e uma mãe não conseguia agendar dois filhos com o
mesmo telefone (o segundo agendamento reescrevia o nome do primeiro).

Princípio: errar sempre para o lado de duplicar, nunca para o lado de
fundir pessoas diferentes -- duplicata é reversível, identidade fundida não é.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.config import settings
from app.models.common import UserRole
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.user import User
from app.services.auth_service import auth_service

LOCAL_TZ = ZoneInfo(settings.timezone)


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def horario_futuro(dias: int, hora: int) -> datetime:
    alvo = (datetime.now(LOCAL_TZ) + timedelta(days=dias)).date()
    return datetime.combine(alvo, time(hora, 0), tzinfo=LOCAL_TZ)


async def _segundo_medico(session) -> tuple[Doctor, str]:
    user = User(
        id="user-doctor-identity-2",
        email="dr.identity2@example.com",
        role=UserRole.doctor,
        full_name="Bruno Identity",
        phone="+5511900009999",
    )
    session.add(user)
    await session.flush()
    doctor_row = Doctor(
        id="doctor-identity-2",
        user_id=user.id,
        slug="dr-identity-2",
        specialty="Pediatria",
        config_json={
            "consultation_duration_minutes": 30,
            "advance_booking_days": 30,
            "auto_confirm": True,
            "cancellation_policy_hours": 24,
            "working_hours": {d: [{"start": "08:00", "end": "18:00"}] for d in (
                "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            )},
        },
    )
    session.add(doctor_row)
    await session.commit()

    class _User:
        id = user.id
        role = UserRole.doctor

    token, _ = auth_service.create_access_token(_User())  # type: ignore[arg-type]
    return doctor_row, token


async def test_mesmo_telefone_nomes_diferentes_cria_dois_pacientes(client, session, doctor, doctor_token) -> None:
    """Mãe agendando pra dois filhos com o mesmo telefone: nomes diferentes,
    tem que virar dois registros -- nunca um sobrescrevendo o outro."""
    payload_base = {"patient_phone": "11955556666"}

    r1 = await client.post(
        "/api/doctors/me/appointments",
        json={**payload_base, "patient_name": "Filho Um", "scheduled_at": horario_futuro(3, 9).isoformat()},
        headers=auth(doctor_token),
    )
    r2 = await client.post(
        "/api/doctors/me/appointments",
        json={**payload_base, "patient_name": "Filho Dois", "scheduled_at": horario_futuro(3, 10).isoformat()},
        headers=auth(doctor_token),
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()["patient_id"] != r2.json()["patient_id"]

    pacientes = (await session.scalars(select(Patient).where(Patient.doctor_id == doctor.id))).all()
    assert {p.name for p in pacientes} == {"Filho Um", "Filho Dois"}


async def test_mesmo_telefone_mesmo_nome_reaproveita_apesar_de_acento_e_caixa(
    client, session, doctor, doctor_token
) -> None:
    r1 = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "José da Silva",
            "patient_phone": "11944445555",
            "scheduled_at": horario_futuro(3, 9).isoformat(),
        },
        headers=auth(doctor_token),
    )
    r2 = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "  jose DA SILVA  ",
            "patient_phone": "11944445555",
            "scheduled_at": horario_futuro(3, 11).isoformat(),
        },
        headers=auth(doctor_token),
    )
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["patient_id"] == r2.json()["patient_id"]

    pacientes = (await session.scalars(select(Patient).where(Patient.doctor_id == doctor.id))).all()
    assert len(pacientes) == 1


async def test_reaproveitamento_nunca_sobrescreve_nome_nem_email(client, session, doctor, doctor_token) -> None:
    r1 = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "Carla Souza",
            "patient_phone": "11933337777",
            "patient_email": "carla@example.com",
            "scheduled_at": horario_futuro(3, 9).isoformat(),
        },
        headers=auth(doctor_token),
    )
    assert r1.status_code == 201

    # Mesmo doctor_id+phone+nome (match exato) -- mas tentando um email diferente.
    r2 = await client.post(
        "/api/doctors/me/appointments",
        json={
            "patient_name": "Carla Souza",
            "patient_phone": "11933337777",
            "patient_email": "outro-email@example.com",
            "scheduled_at": horario_futuro(3, 11).isoformat(),
        },
        headers=auth(doctor_token),
    )
    assert r2.status_code == 201
    assert r1.json()["patient_id"] == r2.json()["patient_id"]

    patient = await session.get(Patient, r1.json()["patient_id"])
    assert patient.email == "carla@example.com"  # não foi sobrescrito


async def test_dois_medicos_mesmo_telefone_e_nome_nao_compartilham_paciente(client, session, doctor, doctor_token) -> None:
    """O que antes era o bug central: dois médicos, mesmo paciente "de fato"
    (mesmo telefone, mesmo nome) -- agora tem que virar dois registros
    completamente separados, um por médico."""
    outro_doctor, outro_token = await _segundo_medico(session)

    payload = {
        "patient_name": "Paciente Compartilhado",
        "patient_phone": "11922223333",
    }
    r1 = await client.post(
        "/api/doctors/me/appointments",
        json={**payload, "scheduled_at": horario_futuro(3, 9).isoformat()},
        headers=auth(doctor_token),
    )
    r2 = await client.post(
        "/api/doctors/me/appointments",
        json={**payload, "scheduled_at": horario_futuro(3, 9).isoformat()},
        headers=auth(outro_token),
    )
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    assert r1.json()["patient_id"] != r2.json()["patient_id"]

    meus_pacientes = (await session.scalars(select(Patient).where(Patient.doctor_id == doctor.id))).all()
    pacientes_do_outro = (await session.scalars(select(Patient).where(Patient.doctor_id == outro_doctor.id))).all()
    assert len(meus_pacientes) == 1
    assert len(pacientes_do_outro) == 1
    assert meus_pacientes[0].id != pacientes_do_outro[0].id

    # E a agenda de um médico não mostra o paciente (nem a consulta) do outro.
    minha_agenda = await client.get("/api/doctors/me/appointments", headers=auth(doctor_token))
    assert all(a["patient_id"] != pacientes_do_outro[0].id for a in minha_agenda.json())
