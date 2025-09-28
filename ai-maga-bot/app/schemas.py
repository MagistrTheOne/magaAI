"""Pydantic models for the application."""

from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class UserMode(str, Enum):
    """User reply mode."""
    AUTO = "auto"
    TEXT = "text"
    VOICE = "voice"


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok", description="Service status")


class WebhookUpdate(BaseModel):
    """Telegram webhook update model."""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    channel_post: Optional[Dict[str, Any]] = None
    edited_channel_post: Optional[Dict[str, Any]] = None


class LLMRequest(BaseModel):
    """Request to LLM service."""
    system_prompt: str = Field(default="You are a helpful AI assistant. Answer briefly and to the point.")
    user_message: str
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    max_tokens: int = Field(default=1200, ge=100, le=6000)


class TTSRequest(BaseModel):
    """Request to TTS service."""
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str = Field(default="alyss")
    format: str = Field(default="oggopus")


class STTRequest(BaseModel):
    """Request to STT service."""
    audio_data: bytes
    format: str = Field(default="oggopus")
    language: str = Field(default="ru-RU")