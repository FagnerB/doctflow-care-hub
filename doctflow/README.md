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
│   ├── models/          # SQLAlchemy
│   ├── schemas/         # Pydantic v2
│   ├── routers/         # auth, doctors, patients, appointments,
│   │                    # schedules, admin, webhooks, tasks
│   ├── services/        # auth, appointment, schedule, notification, email
│   └── tasks/           # reminder_jobs (scheduler de lembretes)
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
- `WHATSAPP_PROVIDER`: `console` por padrão. `twilio` e `http_api` são opcionais.
- `TIMEZONE`: fuso do consultório (`America/Sao_Paulo`). O pacote `tzdata` é
  dependência obrigatória — `python:3.11-slim` e Windows não trazem a base de
  fusos do sistema e sem ela toda a geração de horários falha.
- `CRON_SECRET`: habilita o endpoint de cron dos lembretes.
- `PASSWORD_RESET_PATH`: rota do frontend que recebe o link de reset.

## Fluxo de agendamento

- `GET /api/doctors/{slug}` — perfil público do médico (página `/d/{slug}`).
- `GET /api/doctors/{slug}/availability?date=YYYY-MM-DD` — slots disponíveis.
- `POST /api/appointments` — cria o agendamento público (sem login).
- `GET /api/appointments/{id}/status` — status da consulta pelo link do paciente.

## Recuperação de senha

Delegada ao Supabase Auth (templates ficam no painel do Supabase).

1. `POST /api/auth/forgot-password` `{ "email": "..." }` — dispara o e-mail.
   Responde sempre 200 com a mesma mensagem, exista ou não a conta, para não
   permitir enumeração de usuários. Rate limit de 5 chamadas / 5 min por IP.
2. O link leva o médico a `FRONTEND_URL + PASSWORD_RESET_PATH`, que recebe do
   Supabase um `access_token` (fragmento) ou `token_hash` (query string).
3. `POST /api/auth/reset-password` `{ "new_password": "...", "access_token": "..." }`
   grava a nova senha. Mínimo de 8 caracteres.

`POST /api/admin/doctors/{id}/invite` (owner) reenvia o convite de primeiro acesso.

## WhatsApp

`WHATSAPP_PROVIDER` escolhe o canal: `console` (mock, padrão), `twilio` ou
`http_api`. Sem credenciais o serviço cai automaticamente no mock e apenas
loga a mensagem — nada no fluxo trava por falta de integração.

Mensagens enviadas:

| Evento | Destinatário |
| --- | --- |
| Confirmação do agendamento | Paciente |
| Aviso de nova consulta | Médico |
| Lembrete 24h e 2h | Paciente |
| Recibo de cancelamento | Paciente |
| Aviso de cancelamento | Médico |

Todos os envios ficam registrados em `notification_logs`.

## Lembretes automáticos

Duas formas de acionar, que podem conviver — a idempotência vem de
`notification_logs`, então nenhum paciente recebe lembrete duplicado:

- **Scheduler interno** (padrão): task asyncio no ciclo de vida da API, a cada
  `REMINDERS_INTERVAL_MINUTES`. Desligue com `REMINDERS_SCHEDULER_ENABLED=false`
  se rodar mais de uma réplica.
- **Cron externo**: `POST /api/tasks/reminders/run` com header `X-Cron-Secret`
  igual a `CRON_SECRET`. Sem `CRON_SECRET` configurado o endpoint fica desligado.
- **Manual (owner)**: `POST /api/admin/reminders/run` com JWT de owner.

`REMINDERS_WINDOW_MINUTES` precisa ser maior ou igual a
`REMINDERS_INTERVAL_MINUTES`, senão consultas caem entre duas execuções.

## Webhook de cancelamento

O paciente responde `CANCELAR` na conversa e a próxima consulta ativa dele é
cancelada; o médico recebe aviso no WhatsApp. Os endpoints são autenticados
porque cancelam consulta a partir de um número de telefone:

- `POST /api/webhooks/whatsapp/twilio` — form-urlencoded, valida a assinatura
  `X-Twilio-Signature`. Configure `TWILIO_WEBHOOK_URL` com a URL pública exata
  (atrás do proxy do Railway a URL vista pelo request não confere).
  Responde TwiML, então o paciente recebe a confirmação na mesma conversa.
- `POST /api/webhooks/whatsapp` — JSON, protegido pelo header `X-Webhook-Secret`
  comparado com `WHATSAPP_API_KEY`. Para provedores não-Twilio.

A política `cancellation_policy_hours` do médico é respeitada: fora do prazo o
cancelamento é recusado e o paciente recebe a explicação.

## Bloqueio de agenda

- `POST /api/doctors/me/exceptions` — dia inteiro (só `exception_date`) ou faixa
  (`start_time` + `end_time`). Recusa com 409 se já houver consulta ativa na
  janela: o médico precisa remarcar antes.
- `GET /api/doctors/me/exceptions` / `DELETE /api/doctors/me/exceptions/{id}`.

Bloqueios entram no cálculo de slots em tempo real.

## Relatórios

`GET /api/doctors/me/stats?reference_month=YYYY-MM-DD` devolve o total do mês,
comparecimentos, faltas, cancelamentos, taxa de comparecimento (considerando só
desfechos conhecidos) e as próximas 10 consultas.

## Testes

```bash
pytest
```

Rodam contra SQLite em arquivo temporário; validam regras de negócio e
contratos HTTP sem precisar de Postgres.

## Deploy

- Aponte `DATABASE_URL` para o Supabase Postgres.
- Configure `JWT_SECRET_KEY`, `SUPABASE_*` e `CORS_ORIGINS` no ambiente de produção.
- Execute as migrações antes de subir a aplicação.
- Rode com `uvicorn app.main:app --host 0.0.0.0 --port 8000` ou em um container com `gunicorn`/`uvicorn` workers.

## Observações

- O provider padrão de mensagens é `console`, útil para MVP e testes locais.
- Se quiser envio real por WhatsApp, troque para Twilio e configure as credenciais.
- O cache em Redis para disponibilidade ficou propositalmente fora do caminho crítico e pode ser adicionado depois.
