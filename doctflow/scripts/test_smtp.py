"""Testa o envio SMTP isolado, sem passar pelo fluxo de agendamento.

Usa as mesmas variáveis de ambiente que o app le em produção (SMTP_HOST,
SMTP_PORT, SMTP_USER, SMTP_PASSWORD, MAIL_FROM_EMAIL) e o mesmo aiosmtplib
que app/services/mail_service.py -- só sem o resto da aplicação no meio,
pra ver o erro cru do servidor.

Rodar de uma rede diferente da do Render é o ponto: se funcionar aqui mas
falhar em produção, o problema é a rede de saída do Render bloqueando a
porta, não as credenciais.

Uso (a partir de doctflow/, com o venv ativo e as env vars exportadas):
    python -m scripts.test_smtp destinatario@example.com
    python -m scripts.test_smtp destinatario@example.com --port 2525
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from email.message import EmailMessage

import aiosmtplib


async def main(to_email: str, port_override: int | None) -> None:
    host = os.environ.get("SMTP_HOST", "")
    port = port_override or int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_email = os.environ.get("MAIL_FROM_EMAIL", "")

    missing = [name for name, value in [("SMTP_HOST", host), ("SMTP_USER", user), ("SMTP_PASSWORD", password), ("MAIL_FROM_EMAIL", from_email)] if not value]
    if missing:
        print(f"Faltando no ambiente: {', '.join(missing)}. Exporte antes de rodar.")
        sys.exit(1)

    message = EmailMessage()
    message["From"] = from_email
    message["To"] = to_email
    message["Subject"] = "Teste SMTP -- DoctFlow"
    message.set_content("Se voce recebeu isso, o SMTP esta funcionando.")

    use_implicit_tls = port == 465
    print(f"Conectando em {host}:{port} (user={user}, {'TLS implicito' if use_implicit_tls else 'STARTTLS'})...")

    try:
        await aiosmtplib.send(
            message,
            hostname=host,
            port=port,
            username=user,
            password=password,
            use_tls=use_implicit_tls,
            start_tls=not use_implicit_tls,
            timeout=20,
        )
    except (aiosmtplib.SMTPException, OSError, TimeoutError) as exc:
        print(f"FALHOU: {type(exc).__name__}: {exc}")
        sys.exit(1)

    print("Enviado com sucesso.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("to_email", help="Email de destino do teste")
    parser.add_argument("--port", type=int, default=None, help="Sobrescreve SMTP_PORT (ex: 2525, 465)")
    args = parser.parse_args()
    asyncio.run(main(args.to_email, args.port))
