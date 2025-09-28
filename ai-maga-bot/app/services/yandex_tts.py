"""Yandex TTS service using SpeechKit API."""

import httpx
import time
from typing import Optional
from app.settings import settings
from app.observability.metrics import metrics_collector
from app.observability.logging import tts_logger
from app.cache.lru_cache import response_cache


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
    start_time = time.time()
    voice = voice or settings.yandex_tts_voice
    format = format or settings.yandex_tts_format
    
    # Check cache first
    cached_response = response_cache.get_tts_response(text, voice, format)
    if cached_response is not None:
        tts_logger.info("TTS cache hit", extra_fields={
            "cache_hit": True,
            "text_length": len(text),
            "voice": voice,
            "format": format
        })
        return cached_response
    
    tts_logger.info("TTS cache miss, making API request", extra_fields={
        "cache_hit": False,
        "text_length": len(text),
        "voice": voice,
        "format": format
    })

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
            
            audio_data = response.content
            
            # Cache the response
            response_cache.set_tts_response(text, voice, format, audio_data)
            
            # Record metrics
            duration = time.time() - start_time
            metrics_collector.record_tts_request("success", voice, duration)
            
            tts_logger.info("TTS request successful", extra_fields={
                "duration_seconds": duration,
                "audio_size_bytes": len(audio_data)
            })
            
            return audio_data

    except httpx.HTTPError as e:
        duration = time.time() - start_time
        metrics_collector.record_tts_request("error", voice, duration)
        tts_logger.error(f"TTS HTTP error: {e}", extra_fields={"duration_seconds": duration})
        raise YandexTTSError(f"Yandex TTS API error: {e}")
    except Exception as e:
        duration = time.time() - start_time
        metrics_collector.record_tts_request("error", voice, duration)
        tts_logger.error(f"TTS unexpected error: {e}", extra_fields={"duration_seconds": duration})
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