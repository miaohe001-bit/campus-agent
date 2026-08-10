from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://campus:campus@localhost:5432/campus_agent"
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_model: str = "gpt-4o-mini"
    scheduler_enabled: bool = True
    scheduler_user_id: str = "local-user"
    scheduler_timezone: str = "Asia/Shanghai"
    scheduler_daily_hour: int = 9
    scheduler_daily_minute: int = 0
    qq_email_address: str | None = None
    qq_email_authorization_code: str | None = None
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
