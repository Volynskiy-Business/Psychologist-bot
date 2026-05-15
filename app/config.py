"""Application configuration using Pydantic Settings."""

from pydantic import Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: SecretStr = Field(..., alias="BOT_TOKEN")
    bot_display_name: str = Field("PsySupport AI", alias="BOT_DISPLAY_NAME")

    # OpenRouter
    openrouter_api_key: SecretStr = Field(..., alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL"
    )
    default_model: str = Field("openrouter/free", alias="OPENROUTER_MODEL")

    # Database
    database_url: SecretStr = Field(..., alias="DATABASE_URL")
    redis_url: RedisDsn = Field("redis://redis:6379/0", alias="REDIS_URL")

    # Admin
    admin_telegram_ids: list[int] = Field(default_factory=list, alias="ADMIN_TELEGRAM_IDS")

    # Privacy
    store_conversations: bool = Field(False, alias="STORE_CONVERSATIONS")
    message_retention_days: int = Field(30, alias="MESSAGE_RETENTION_DAYS")
    safety_event_retention_days: int = Field(180, alias="SAFETY_EVENT_RETENTION_DAYS")

    # App
    app_env: str = Field("development", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()
