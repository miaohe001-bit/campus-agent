from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://campus:campus@localhost:5432/campus_agent"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    app_encryption_key: str | None = None
    scheduler_enabled: bool = True
    scheduler_user_id: str = "local-user"
    scheduler_timezone: str = "Asia/Shanghai"
    scheduler_daily_hour: int = 9
    scheduler_daily_minute: int = 0
    qq_imap_host: str = "imap.qq.com"
    qq_imap_port: int = 993
    qq_imap_mailbox: str = "INBOX"
    qq_imap_fetch_limit: int = 20
    qq_email_sync_enabled: bool = True
    qq_email_sync_interval_hours: int = 6
    monitoring_pipeline_enabled: bool = True
    monitoring_pipeline_interval_hours: int = 6
    wxpublic_app_id: str | None = None
    wxpublic_secure_key: str | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def use_psycopg_driver(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
