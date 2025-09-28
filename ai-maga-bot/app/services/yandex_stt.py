"""Yandex STT service using SpeechKit API."""

import httpx
from typing import Optional
from app.settings import settings


class YandexSTTError(Exception):
    """Exception for Yandex STT errors."""
    pass


async def recognize_speech(
    audio_data: bytes,
    format: str = "oggopus",
    language: str = "ru-RU"
) -> str:
    """
    Recognize speech using Yandex SpeechKit.

    Args:
        audio_data: Audio data as bytes
        format: Audio format
        language: Language code

    Returns:
        Recognized text

    Raises:
        YandexSTTError: If the API call fails
    """
    if not settings.yandex_stt_enable:
        raise YandexSTTError("STT is disabled in settings")

    data = {
        "audio": audio_data,
        "format": format,
        "languageCode": language,
    }

    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize",
                headers=headers,
                data=data
            )
            response.raise_for_status()

            result = response.json()
            return result.get("result", "").strip()

    except httpx.HTTPError as e:
        raise YandexSTTError(f"Yandex STT API error: {e}")
    except Exception as e:
        raise YandexSTTError(f"Unexpected error: {e}")


async def recognize_with_request(request: "STTRequest") -> str:
    """
    Recognize speech using STTRequest model.

    Args:
        request: STTRequest instance

    Returns:
        Recognized text
    """
    return await recognize_speech(
        audio_data=request.audio_data,
        format=request.format,
        language=request.language
    )