# DoctFlow API

Backend do DoctFlow em FastAPI, SQLAlchemy assíncrono, Pydantic v2 e integração preparada para Supabase Auth/PostgreSQL.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 async
- Pydantic v2
- Supabase Auth via API REST
- python-jose para JWT
- WhatsApp via provider opcional em console ou Twilio

## Estrutura

```text
/doctflow
├── app/
├── alembic/
├── tests/
├── requirements.txt
├── .env.example
└── README.md
```

## Como rodar localmente

1. Entre na pasta do backend:

```bash
cd doctflow
```

2. Crie o ambiente e instale dependências:

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

3. Configure as variáveis:

```bash
copy .env.example .env
```

4. Inicie o banco local ou aponte `DATABASE_URL` para o Supabase Postgres.

5. Rode as migrações:

```bash
alembic upgrade head
```

6. Suba a API:

```bash
uvicorn app.main:app --reload --port 8000
```

## Migrações

A pasta `alembic/` já vem pronta. O revision inicial cria todas as tabelas principais do domínio.

Comandos úteis:

```bash
alembic revision --autogenerate -m "nova alteracao"
alembic upgrade head
alembic downgrade -1
```

## Variáveis importantes

- `DATABASE_URL`: string async do Postgres/Supabase.
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`: usadas para login, refresh, recovery e criação de conta médica.
- `JWT_SECRET_KEY`: assinatura do token da API.
- `WHATSAPP_PROVIDER`: `console` por padrão. `twilio` é opcional.

## Fluxo de agendamento

- `GET /api/doctors/{slug}/availability?date=YYYY-MM-DD` retorna slots disponíveis.
- `POST /api/appointments` cria o agendamento público.
- `POST /api/appointments/webhook/whatsapp` processa mensagens como `CANCELAR`.
- `POST /api/admin/reminders/run` dispara lembretes 24h e 2h via cron.

## Deploy

- Aponte `DATABASE_URL` para o Supabase Postgres.
- Configure `JWT_SECRET_KEY`, `SUPABASE_*` e `CORS_ORIGINS` no ambiente de produção.
- Execute as migrações antes de subir a aplicação.
- Rode com `uvicorn app.main:app --host 0.0.0.0 --port 8000` ou em um container com `gunicorn`/`uvicorn` workers.

## Observações

- O provider padrão de mensagens é `console`, útil para MVP e testes locais.
- Se quiser envio real por WhatsApp, troque para Twilio e configure as credenciais.
- O cache em Redis para disponibilidade ficou propositalmente fora do caminho crítico e pode ser adicionado depois.
