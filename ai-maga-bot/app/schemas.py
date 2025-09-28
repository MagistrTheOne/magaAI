"""
Pydantic модели для валидации данных.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field


class WebhookUpdate(BaseModel):
    """Модель для Telegram webhook update."""
    update_id: int
    message: Optional[dict] = None
    edited_message: Optional[dict] = None
    channel_post: Optional[dict] = None
    edited_channel_post: Optional[dict] = None


class UserMode(BaseModel):
    """Режим ответа пользователя."""
    mode: Literal["auto", "text", "voice"] = Field(default="auto")
    user_id: int


class LLMRequest(BaseModel):
    """Запрос к Yandex LLM."""
    system_prompt: str = Field(default="Ты полезный AI-ассистент. Отвечай кратко и по делу.")
    user_message: str
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1200, ge=100, le=6000)


class TTSRequest(BaseModel):
    """Запрос к Yandex TTS."""
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(default="alyss")
    format: str = Field(default="oggopus")


class STTRequest(BaseModel):
    """Запрос к Yandex STT."""
    audio_data: bytes
    format: str = Field(default="oggopus")
    language: str = Field(default="ru-RU")


class HealthResponse(BaseModel):
    """Ответ health check."""
    status: Literal["ok"] = "ok"
