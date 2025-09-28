"""
Настройки приложения с валидацией переменных окружения.
"""
import os
import logging
from typing import Optional
from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Настройки приложения."""
    
    # Telegram
    telegram_bot_token: str = Field(..., description="Токен Telegram бота")
    telegram_webhook_secret: str = Field(..., description="Секрет для вебхука")
    base_public_url: str = Field(..., description="Публичный URL приложения")
    
    # Providers
    llm_provider: str = Field(default="yandex", description="LLM провайдер (yandex)")
    tts_provider: str = Field(default="yandex", description="TTS провайдер (yandex|elevenlabs)")
    
    # Yandex Cloud
    yandex_api_key: str = Field(..., description="API ключ Yandex Cloud")
    yandex_folder_id: str = Field(..., description="ID папки Yandex Cloud")
    yandex_llm_model: str = Field(..., description="Модель LLM (gpt://catalog-id/model)")
    yandex_model_uri: Optional[str] = Field(default=None, description="Алиас для модели LLM")
    yandex_tts_voice: str = Field(default="alyss", description="Голос для TTS")
    yandex_tts_format: str = Field(default="oggopus", description="Формат аудио TTS")
    yandex_stt_enable: bool = Field(default=False, description="Включить STT")
    yandex_translate_enabled: bool = Field(default=False, description="Включить перевод")
    yandex_vision_enabled: bool = Field(default=False, description="Включить визион")
    
    # ElevenLabs
    elevenlabs_api_key: Optional[str] = Field(default=None, description="API ключ ElevenLabs")
    elevenlabs_voice_id: Optional[str] = Field(default=None, description="ID голоса Liam")
    elevenlabs_model_id: str = Field(default="eleven_multilingual_v2", description="Модель ElevenLabs")
    elevenlabs_output_format: str = Field(default="mp3_44100_128", description="Формат аудио ElevenLabs")
    elevenlabs_convert_to_ogg: bool = Field(default=False, description="Конвертировать в OGG/OPUS")
    
    # Server
    port: int = Field(default=8080, description="Порт сервера")
    log_level: str = Field(default="INFO", description="Уровень логирования")
    
    # Вычисляемые поля
    webhook_path: str = Field(default="", description="Путь вебхука")
    webhook_url: str = Field(default="", description="Полный URL вебхука")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @validator("webhook_path", always=True)
    def set_webhook_path(cls, v, values):
        """Вычисляем путь вебхука."""
        secret = values.get("telegram_webhook_secret")
        if secret:
            return f"/webhook/telegram/{secret}"
        return v
    
    @validator("webhook_url", always=True)
    def set_webhook_url(cls, v, values):
        """Вычисляем полный URL вебхука."""
        base_url = values.get("base_public_url", "").rstrip("/")
        webhook_path = values.get("webhook_path", "")
        if base_url and webhook_path:
            return f"{base_url}{webhook_path}"
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Валидируем уровень логирования."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level должен быть одним из: {valid_levels}")
        return v.upper()
    
    @validator("llm_provider")
    def validate_llm_provider(cls, v):
        """Валидируем LLM провайдер."""
        valid_providers = ["yandex"]
        if v.lower() not in valid_providers:
            raise ValueError(f"llm_provider должен быть одним из: {valid_providers}")
        return v.lower()
    
    @validator("tts_provider")
    def validate_tts_provider(cls, v):
        """Валидируем TTS провайдер."""
        valid_providers = ["yandex", "elevenlabs"]
        if v.lower() not in valid_providers:
            raise ValueError(f"tts_provider должен быть одним из: {valid_providers}")
        return v.lower()
    
    @validator("yandex_llm_model", always=True)
    def set_llm_model(cls, v, values):
        """Устанавливаем модель LLM с приоритетом yandex_model_uri."""
        model_uri = values.get("yandex_model_uri")
        if model_uri:
            return model_uri
        return v


def setup_logging(log_level: str = "INFO") -> None:
    """Настройка логирования."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ]
    )


def get_settings() -> Settings:
    """Получить настройки приложения."""
    return Settings()


# Глобальный экземпляр настроек
settings = get_settings()

# Настройка логирования
setup_logging(settings.log_level)
