"""
Сервис для работы с Yandex SpeechKit TTS.
"""
import logging
from typing import Optional
import httpx
from httpx import HTTPStatusError, TimeoutException

from app.settings import settings
from app.schemas import TTSRequest

logger = logging.getLogger(__name__)


class YandexTTSError(Exception):
    """Ошибка при работе с Yandex TTS."""
    """Yandex SpeechKit TTS провайдер."""
    pass


async def synthesize_speech(
    text: str,
    voice: str = "alyss",
    format: str = "oggopus"
) -> bytes:
    """
    Синтезировать речь через Yandex SpeechKit TTS.
    
    Args:
        text: Текст для синтеза
        voice: Голос для синтеза
        format: Формат аудио (oggopus для Telegram)
        
    Returns:
        bytes: Аудио данные
        
    Raises:
        YandexTTSError: При ошибке API или сети
    """
    if not text.strip():
        raise YandexTTSError("Пустой текст для синтеза")
    
    if len(text) > 5000:
        raise YandexTTSError("Текст слишком длинный (максимум 5000 символов)")
    
    data = {
        "text": text,
        "voice": voice,
        "format": format
    }
    
    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug(f"Отправляем запрос к Yandex TTS: {text[:50]}...")
            
            response = await client.post(
                "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize",
                headers=headers,
                data=data
            )
            
            response.raise_for_status()
            
            audio_data = response.content
            if not audio_data:
                raise YandexTTSError("Пустые аудио данные от TTS")
            
            logger.debug(f"Получены аудио данные: {len(audio_data)} байт")
            return audio_data
            
    except HTTPStatusError as e:
        logger.error(f"HTTP ошибка при запросе к Yandex TTS: {e.response.status_code} - {e.response.text}")
        raise YandexTTSError(f"Ошибка API Yandex TTS: {e.response.status_code}")
    except TimeoutException:
        logger.error("Таймаут при запросе к Yandex TTS")
        raise YandexTTSError("Таймаут при запросе к Yandex TTS")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к Yandex TTS: {e}")
        raise YandexTTSError(f"Ошибка при запросе к Yandex TTS: {e}")


async def synthesize_with_request(request: TTSRequest) -> bytes:
    """
    Синтезировать речь с использованием Pydantic модели.
    
    Args:
        request: Модель запроса к TTS
        
    Returns:
        bytes: Аудио данные
    """
    return await synthesize_speech(
        text=request.text,
        voice=request.voice,
        format=request.format
    )
