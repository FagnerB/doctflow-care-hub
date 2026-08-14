"""Remove patients.cpf.

Campo nunca foi coletado por nenhuma tela e a única rota que o expunha
(GET /patients/{id}) vazava CPF de qualquer paciente para qualquer médico
autenticado (IDOR corrigido junto). Minimização de dado: não guarda o que
não precisa para agendar.

Revision ID: 0003_remove_patient_cpf
Revises: 0002_unique_active_slot
Create Date: 2026-08-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "0003_remove_patient_cpf"
down_revision = "0002_unique_active_slot"
branch_labels = None
depends_on = None


def _has_column(bind, table: str, column: str) -> bool:
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def upgrade() -> None:
    # Idempotente: em banco novo, a migration 0001 já cria as tabelas a partir
    # dos models ATUAIS (sem cpf) -- essa coluna nunca existe pra dropar. Em
    # produção (rodou 0001 antes de cpf sair do model), ela existe de verdade
    # e é removida normalmente.
    bind = op.get_bind()
    if _has_column(bind, "patients", "cpf"):
        op.drop_column("patients", "cpf")


def downgrade() -> None:
    bind = op.get_bind()
    if not _has_column(bind, "patients", "cpf"):
        op.add_column("patients", sa.Column("cpf", sa.String(length=20), nullable=True))
