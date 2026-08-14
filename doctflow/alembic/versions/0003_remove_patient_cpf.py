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

revision = "0003_remove_patient_cpf"
down_revision = "0002_unique_active_slot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("patients", "cpf")


def downgrade() -> None:
    op.add_column("patients", sa.Column("cpf", sa.String(length=20), nullable=True))
