from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="before")
    @classmethod
    def _strip_whitespace(cls, data: object) -> object:
        """Remove espaço/quebra de linha nas pontas de toda variável de ambiente.

        Copiar um valor de um bloco de código (ex.: uma DATABASE_URL) costuma
        trazer uma quebra de linha invisível no final. Isso já causou
        `InvalidCatalogNameError: database "postgres\\n" does not exist` em
        produção — a variável parecia certa no painel do Railway, mas tinha
        um caractere de controle colado no fim. Mais seguro sanear aqui do
        que confiar que toda edição futura de env var vai vir limpa.
        """
        if not isinstance(data, dict):
            return data
        return {key: value.strip() if isinstance(value, str) else value for key, value in data.items()}

    app_name: str = "DoctFlow API"
    api_prefix: str = "/api"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    database_url: str = Field(default="sqlite+aiosqlite:///./doctflow.db")
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    frontend_url: str = "http://localhost:3000"
    dashboard_url: str = "http://localhost:3000/dashboard"
    public_base_url: str = "http://localhost:8000"

    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 30

    timezone: str = "America/Sao_Paulo"
    default_consultation_duration_minutes: int = 30
    default_advance_booking_days: int = 30
    default_cancellation_policy_hours: int = 24

    whatsapp_provider: str = "console"
    whatsapp_api_key: str = ""
    whatsapp_api_url: str = ""
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""
    # Valida a assinatura X-Twilio-Signature do webhook. Só desligue em teste local.
    twilio_validate_signature: bool = True
    # URL pública exata que a Twilio chama; usada no cálculo da assinatura.
    # Se vazia, cai para a URL vista pelo request (pode falhar atrás de proxy).
    twilio_webhook_url: str = ""

    # Email transacional de conteúdo livre (confirmação/cancelamento de consulta).
    # Diferente do supabase_url acima, que só cobre os fluxos fixos de Auth.
    # console (padrão) = modo mock, só loga. smtp = envia de verdade.
    mail_provider: str = "console"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from_email: str = ""
    # Nome de exibição padrão; o email de confirmação de consulta usa o nome
    # do médico em vez disso (o paciente precisa reconhecer quem está avisando).
    mail_from_name: str = "DoctFlow"
    mail_reply_to: str = ""

    # Caminho no frontend onde o médico define a nova senha (link do e-mail).
    password_reset_path: str = "/reset-password"
    # Segredo do endpoint de cron dos lembretes (header X-Cron-Secret).
    # Vazio = endpoint de cron desabilitado.
    cron_secret: str = ""
    # Scheduler interno de lembretes (roda dentro do processo da API).
    reminders_scheduler_enabled: bool = True
    reminders_interval_minutes: int = 60
    # Tolerância da janela de busca de lembretes; precisa ser >= o intervalo
    # do scheduler, senão consultas caem entre duas execuções e não recebem aviso.
    reminders_window_minutes: int = 75

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def password_reset_url(self) -> str:
        """URL para onde o Supabase redireciona após o clique no e-mail de reset."""
        return f"{self.frontend_url.rstrip('/')}{self.password_reset_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
