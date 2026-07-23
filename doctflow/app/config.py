from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
