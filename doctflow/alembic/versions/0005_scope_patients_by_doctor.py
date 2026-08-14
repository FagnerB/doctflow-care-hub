"""Escopa patients por médico (doctor_id + nome normalizado na identidade).

patients era uma tabela global: phone era unique=True sem nenhuma coluna
ligando ao médico. Consequência real, achada nesta rodada: dois médicos
podiam acabar compartilhando o mesmo registro de paciente (nome/e-mail
sobrescritos por quem agendasse por último), GET /patients/{id} vazava
paciente de um médico pro outro (IDOR, corrigido em migration separada), e
uma mãe não conseguia agendar dois filhos com o mesmo telefone -- o segundo
agendamento reescrevia o nome do primeiro.

Pré-requisito: rodar scripts/clear_test_patients.py --confirm antes desta
migration. Ela se recusa a rodar em produção se `patients` não estiver
vazia -- não existe médico correto pra atribuir a um paciente que nunca
teve um, então backfill não é uma opção aqui (decisão tomada com o dono do
projeto: base é toda de teste, nada a preservar).

Revision ID: 0005_scope_patients_by_doctor
Revises: 0004_notification_status_simulated
Create Date: 2026-08-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "0005_scope_patients_by_doctor"
down_revision = "0004_notification_status_simulated"
branch_labels = None
depends_on = None

OLD_UNIQUE_INDEX = "ix_patients_phone"
NEW_UNIQUE_CONSTRAINT = "uq_patients_doctor_phone_name"


def _has_column(bind, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if _has_column(bind, "patients", "doctor_id"):
        # Banco novo: a migration 0001 já criou a tabela a partir dos models
        # ATUAIS (Base.metadata.create_all), que já têm doctor_id/name_key e
        # o UniqueConstraint novo desde o início. Nada a fazer.
        return

    count = bind.execute(text("SELECT COUNT(*) FROM patients")).scalar_one()
    if count:
        raise RuntimeError(
            f"patients tem {count} linha(s) -- rode "
            "`python -m scripts.clear_test_patients --confirm` antes desta migration. "
            "Sem isso não há médico correto pra atribuir a doctor_id (NOT NULL)."
        )

    # batch_alter_table: no Postgres emite ALTER normal; no SQLite (dev local
    # com um doctflow.db antigo, de antes desta migration) faz o
    # copy-and-move que o dialeto exige pra ADD COLUMN com FK -- achei essa
    # exigência testando a migration contra uma tabela no formato antigo.
    with op.batch_alter_table("patients") as batch_op:
        batch_op.add_column(
            sa.Column("doctor_id", sa.String(length=36), sa.ForeignKey("doctors.id", ondelete="CASCADE"), nullable=False)
        )
        batch_op.add_column(sa.Column("name_key", sa.String(length=255), nullable=False))
        # Índice único antigo (unique=True + index=True em phone sozinho) --
        # criado pela 0001 quando o model ainda não tinha doctor_id.
        batch_op.drop_index(OLD_UNIQUE_INDEX)
        batch_op.create_unique_constraint(NEW_UNIQUE_CONSTRAINT, ["doctor_id", "phone", "name_key"])


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "patients", "doctor_id"):
        return

    # Falha de propósito se telefones duplicados entre médicos existirem
    # agora -- não há como decidir sozinho qual registro "vence" o antigo
    # índice único global.
    with op.batch_alter_table("patients") as batch_op:
        batch_op.drop_constraint(NEW_UNIQUE_CONSTRAINT, type_="unique")
        batch_op.drop_column("name_key")
        batch_op.drop_column("doctor_id")
        batch_op.create_index(OLD_UNIQUE_INDEX, ["phone"], unique=True)
