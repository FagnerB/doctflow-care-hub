"""Índice único parcial impedindo duas consultas ativas no mesmo horário.

A validação de slot em Python sofre corrida: dois pacientes que enviam o
formulário ao mesmo tempo passam os dois pela checagem antes de qualquer commit.
Só o banco resolve isso. O índice é parcial para que consultas canceladas não
bloqueiem a reutilização do horário.

Revision ID: 0002_unique_active_slot
Revises: 0001_initial
Create Date: 2026-08-11
"""

from __future__ import annotations

from alembic import op

revision = "0002_unique_active_slot"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_appointments_active_slot"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (usado nos testes) não precisa: não há concorrência real ali.
        return

    # Remove duplicatas pré-existentes antes de criar o índice, mantendo a
    # consulta mais antiga de cada horário e cancelando as demais.
    op.execute(
        """
        WITH duplicadas AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY doctor_id, scheduled_at
                       ORDER BY created_at ASC, id ASC
                   ) AS posicao
            FROM appointments
            WHERE status IN ('pending', 'confirmed')
        )
        UPDATE appointments
        SET status = 'cancelled_by_doctor'
        WHERE id IN (SELECT id FROM duplicadas WHERE posicao > 1)
        """
    )

    op.execute(
        f"""
        CREATE UNIQUE INDEX IF NOT EXISTS {INDEX_NAME}
        ON appointments (doctor_id, scheduled_at)
        WHERE status IN ('pending', 'confirmed')
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
