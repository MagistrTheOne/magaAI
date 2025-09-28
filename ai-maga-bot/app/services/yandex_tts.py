"""Yandex TTS service using SpeechKit API."""

import httpx
from typing import Optional
from app.settings import settings


class YandexTTSError(Exception):
    """Exception for Yandex TTS errors."""
    pass


async def synthesize_speech(
    text: str,
    voice: Optional[str] = None,
    format: Optional[str] = None
) -> bytes:
    """
    Synthesize speech using Yandex SpeechKit.

    Args:
        text: Text to synthesize
        voice: Voice to use (optional, uses settings default)
        format: Audio format (optional, uses settings default)

    Returns:
        Audio data as bytes

    Raises:
        YandexTTSError: If the API call fails
    """
    voice = voice or settings.yandex_tts_voice
    format = format or settings.yandex_tts_format

    data = {
        "text": text,
        "voice": voice,
        "format": format,
    }

    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
                headers=headers,
                data=data
            )
            response.raise_for_status()

            return response.content

    except httpx.HTTPError as e:
        raise YandexTTSError(f"Yandex TTS API error: {e}")
    except Exception as e:
        raise YandexTTSError(f"Unexpected error: {e}")


async def synthesize_with_request(request: "TTSRequest") -> bytes:
    """
    Synthesize speech using TTSRequest model.

    Args:
        request: TTSRequest instance

    Returns:
        Audio data as bytes
    """
    return await synthesize_speech(
        text=request.text,
        voice=request.voice,
        format=request.format
    )