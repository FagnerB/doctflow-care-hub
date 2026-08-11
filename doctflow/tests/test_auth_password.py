"""Recuperação e redefinição de senha."""

from __future__ import annotations


from app.config import settings
from app.services.email_service import email_service


async def test_forgot_password_responde_generico_para_email_existente(client, doctor) -> None:
    response = await client.post("/api/auth/forgot-password", json={"email": "dr.silva@example.com"})
    assert response.status_code == 200
    assert response.json()["success"] is True


async def test_forgot_password_nao_permite_enumerar_contas(client, doctor) -> None:
    """Conta existente e inexistente precisam devolver exatamente a mesma resposta."""
    existente = await client.post("/api/auth/forgot-password", json={"email": "dr.silva@example.com"})

    from app.dependencies import _rate_buckets

    _rate_buckets.clear()  # o rate limit é por IP e as duas chamadas vêm do mesmo

    inexistente = await client.post("/api/auth/forgot-password", json={"email": "ninguem@example.com"})

    assert existente.status_code == inexistente.status_code == 200
    assert existente.json() == inexistente.json()


async def test_forgot_password_valida_email(client) -> None:
    response = await client.post("/api/auth/forgot-password", json={"email": "nao-e-email"})
    assert response.status_code == 422


async def test_forgot_password_tem_rate_limit(client, doctor) -> None:
    """Sem limite, o endpoint vira ferramenta de spam de e-mail."""
    codigos = []
    for _ in range(7):
        response = await client.post("/api/auth/forgot-password", json={"email": "dr.silva@example.com"})
        codigos.append(response.status_code)
    assert 429 in codigos


async def test_reset_password_exige_token(client) -> None:
    response = await client.post("/api/auth/reset-password", json={"new_password": "senhaSegura123"})
    assert response.status_code == 422


async def test_reset_password_exige_senha_forte(client) -> None:
    response = await client.post(
        "/api/auth/reset-password",
        json={"new_password": "123", "access_token": "token-qualquer"},
    )
    assert response.status_code == 422


async def test_reset_password_sem_supabase_configurado(client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "supabase_url", "")
    response = await client.post(
        "/api/auth/reset-password",
        json={"new_password": "senhaSegura123", "access_token": "token-qualquer"},
    )
    assert response.status_code == 401


async def test_email_service_entra_em_mock_sem_supabase(monkeypatch) -> None:
    monkeypatch.setattr(settings, "supabase_url", "")
    monkeypatch.setattr(settings, "supabase_anon_key", "")

    resultado = await email_service.send_password_recovery("qualquer@example.com")

    assert resultado.ok is True
    assert resultado.provider == "console"


def test_url_de_reset_aponta_para_o_frontend(monkeypatch) -> None:
    monkeypatch.setattr(settings, "frontend_url", "https://app.doctflow.com/")
    monkeypatch.setattr(settings, "password_reset_path", "/reset-password")
    assert settings.password_reset_url == "https://app.doctflow.com/reset-password"
