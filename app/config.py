"""Application configuration using Pydantic Settings."""

from pydantic import Field, RedisDsn, SecretStr, model_validator
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
    classifier_model: str = Field("", alias="CLASSIFIER_MODEL")
    fallback_models_raw: str = Field("", alias="OPENROUTER_FALLBACK_MODELS")

    @property
    def fallback_models(self) -> list[str]:
        if not self.fallback_models_raw:
            return []
        return [x.strip() for x in self.fallback_models_raw.split(",") if x.strip()]

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
    allow_free_models: bool = Field(False, alias="ALLOW_FREE_MODELS")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @model_validator(mode="after")
    def _reject_free_models_unless_allowed(self) -> "Settings":
        if self.app_env.lower() == "development" and self.allow_free_models:
            return self
        candidates = [self.default_model]
        if self.classifier_model:
            candidates.append(self.classifier_model)
        candidates.extend(
            x.strip() for x in self.fallback_models_raw.split(",") if x.strip()
        )
        for model in candidates:
            if model.endswith(":free"):
                raise ValueError(
                    f"Model '{model}' ends with ':free'. "
                    "Free models are only allowed when APP_ENV=development "
                    "and ALLOW_FREE_MODELS=true."
                )
        return self


settings = Settings()
