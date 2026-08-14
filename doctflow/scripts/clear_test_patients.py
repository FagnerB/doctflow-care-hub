"""Apaga TODO o conteúdo de patients/appointments/notification_logs.

Pré-requisito da migration 0005 (doctor_id obrigatório em patients): a base
hoje é toda de dado de teste (confirmado com o dono do projeto -- ver
alembic/versions/0005_scope_patients_by_doctor.py), sem nenhum paciente
compartilhado entre médicos e nada a preservar. Backfill não se aplica: não
existe médico correto pra atribuir a um paciente que nunca teve um.

Ordem das DELETE importa por causa das FKs:
  1. notification_logs -- referencia appointments (ondelete=CASCADE, mas
     apagado explicitamente aqui em vez de confiar só no cascade)
  2. appointments       -- referencia patients (ondelete=RESTRICT: apagar
     patients primeiro quebraria com FK violation)
  3. patients

NÃO faz parte da migration de propósito: apagar dado merece revisão
explícita, separada de "rodar migration" (que devia ser sempre seguro em CI).

Uso (a partir de doctflow/, com o venv ativo):
    python -m scripts.clear_test_patients            # só mostra as contagens
    python -m scripts.clear_test_patients --confirm   # apaga de verdade
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import text

from app.database import engine

TABLES_IN_DELETE_ORDER = ["notification_logs", "appointments", "patients"]


async def _counts(conn) -> dict[str, int]:
    result = {}
    for table in TABLES_IN_DELETE_ORDER:
        count = await conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
        result[table] = count.scalar_one()
    return result


def _print_counts(label: str, counts: dict[str, int]) -> None:
    print(label)
    for table, count in counts.items():
        print(f"  {table}: {count}")


async def main(confirm: bool) -> None:
    async with engine.connect() as conn:
        print(f"Alvo: {conn.engine.url.render_as_string(hide_password=True)}\n")
        _print_counts("Antes:", await _counts(conn))

    if not confirm:
        print("\nModo dry-run -- nada foi apagado. Rode com --confirm pra apagar de verdade.")
        return

    async with engine.begin() as conn:
        for table in TABLES_IN_DELETE_ORDER:
            await conn.execute(text(f"DELETE FROM {table}"))

    async with engine.connect() as conn:
        _print_counts("\nDepois:", await _counts(conn))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--confirm", action="store_true", help="Apaga de verdade. Sem essa flag só mostra as contagens.")
    args = parser.parse_args()
    asyncio.run(main(args.confirm))
