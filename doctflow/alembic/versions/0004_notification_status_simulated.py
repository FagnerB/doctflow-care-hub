"""Adiciona 'simulated' ao enum notification_status.

O provider em modo mock (console) não entrega nada de verdade -- só loga.
Antes disso, o log gravava 'sent' mesmo assim, então um paciente reclamando
"não recebi aviso" não tinha como ser diferenciado de uma falha real. Bancos
novos já criam o enum certo (migration 0001 usa os models atuais); esta
migration atualiza bancos que já rodaram 0001 antes dessa mudança.

Revision ID: 0004_notification_status_simulated
Revises: 0003_remove_patient_cpf
Create Date: 2026-08-14
"""

from __future__ import annotations

from alembic import op

revision = "0004_notification_status_simulated"
down_revision = "0003_remove_patient_cpf"
branch_labels = None
depends_on = None

ENUM_NAME = "notification_status"
OLD_VALUES = ("sent", "delivered", "failed")
NEW_VALUE = "simulated"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (testes) não tem enum nativo -- os models já têm o valor novo.
        return
    op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_VALUE}'")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Postgres não permite remover valor de enum diretamente: recria o tipo
    # sem 'simulated'. Falha (de propósito) se alguma linha ainda usa esse
    # valor -- não há como fazer downgrade sem decidir pra qual status
    # remapear essas linhas, e essa decisão não é nossa pra tomar aqui.
    op.execute(f"ALTER TYPE {ENUM_NAME} RENAME TO {ENUM_NAME}_old")
    values = ", ".join(f"'{value}'" for value in OLD_VALUES)
    op.execute(f"CREATE TYPE {ENUM_NAME} AS ENUM ({values})")
    op.execute(
        f"ALTER TABLE notification_logs ALTER COLUMN status TYPE {ENUM_NAME} "
        f"USING status::text::{ENUM_NAME}"
    )
    op.execute(f"DROP TYPE {ENUM_NAME}_old")
