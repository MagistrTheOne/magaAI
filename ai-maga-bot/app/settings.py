"""Application settings with Pydantic and environment variables."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    # Telegram
    telegram_bot_token: str = Field(..., description="Telegram bot token")
    telegram_webhook_secret: str = Field(..., description="Webhook secret for validation")

    # Public URL
    base_public_url: str = Field(..., description="Base public URL for webhooks")

    # Yandex Cloud
    yandex_api_key: str = Field(..., description="Yandex Cloud API key")
    yandex_folder_id: str = Field(..., description="Yandex Cloud folder ID")
    yandex_llm_model: str = Field(..., description="Yandex LLM model URI")
    yandex_tts_voice: str = Field(default="alyss", description="TTS voice")
    yandex_tts_format: str = Field(default="oggopus", description="TTS audio format")
    yandex_stt_enable: bool = Field(default=False, description="Enable STT functionality")

    # Server
    port: int = Field(default=8080, description="Server port")
    log_level: str = Field(default="INFO", description="Logging level")

    # Computed fields
    webhook_path: str = Field(default="", description="Webhook path")
    webhook_url: str = Field(default="", description="Full webhook URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("webhook_path", always=True)
    def set_webhook_path(cls, v, values):
        """Set webhook path based on secret."""
        secret = values.get("telegram_webhook_secret", "")
        return f"/webhook/telegram/{secret}"

    @validator("webhook_url", always=True)
    def set_webhook_url(cls, v, values):
        """Set full webhook URL."""
        base_url = values.get("base_public_url", "").rstrip("/")
        path = values.get("webhook_path", "")
        return f"{base_url}{path}"

    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()


# Global settings instance
settings = Settings()