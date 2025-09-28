"""
Сервис для работы с ElevenLabs TTS v2.
"""
import logging
from typing import Optional
import httpx
from httpx import HTTPStatusError, TimeoutException

from app.settings import settings
from app.schemas import TTSRequest

logger = logging.getLogger(__name__)


class ElevenLabsTTSError(Exception):
    """Ошибка при работе с ElevenLabs TTS."""
    pass


async def synthesize_elevenlabs(
    text: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    output_format: Optional[str] = None
) -> bytes:
    """
    Синтезировать речь через ElevenLabs TTS v2.
    
    Args:
        text: Текст для синтеза
        voice_id: ID голоса (по умолчанию из настроек)
        model_id: ID модели (по умолчанию eleven_multilingual_v2)
        output_format: Формат аудио (по умолчанию mp3_44100_128)
        
    Returns:
        bytes: Аудио данные (mp3)
        
    Raises:
        ElevenLabsTTSError: При ошибке API или сети
    """
    if not text.strip():
        raise ElevenLabsTTSError("Пустой текст для синтеза")
    
    if len(text) > 5000:
        raise ElevenLabsTTSError("Текст слишком длинный (максимум 5000 символов)")
    
    # Используем настройки по умолчанию
    voice_id = voice_id or settings.elevenlabs_voice_id
    model_id = model_id or settings.elevenlabs_model_id
    output_format = output_format or settings.elevenlabs_output_format
    
    if not voice_id:
        raise ElevenLabsTTSError("Не указан voice_id для ElevenLabs")
    
    if not settings.elevenlabs_api_key:
        raise ElevenLabsTTSError("Не настроен API ключ ElevenLabs")
    
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    headers = {
        "xi-api-key": settings.elevenlabs_api_key,
        "Content-Type": "application/json"
    }
    
    # Параметры запроса
    params = {
        "output_format": output_format
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug(f"Отправляем запрос к ElevenLabs TTS: {text[:50]}...")
            
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers=headers,
                json=payload,
                params=params
            )
            
            response.raise_for_status()
            
            audio_data = response.content
            if not audio_data:
                raise ElevenLabsTTSError("Пустые аудио данные от ElevenLabs TTS")
            
            logger.debug(f"Получены аудио данные от ElevenLabs: {len(audio_data)} байт")
            return audio_data
            
    except HTTPStatusError as e:
        logger.error(f"HTTP ошибка при запросе к ElevenLabs TTS: {e.response.status_code} - {e.response.text}")
        raise ElevenLabsTTSError(f"Ошибка API ElevenLabs TTS: {e.response.status_code}")
    except TimeoutException:
        logger.error("Таймаут при запросе к ElevenLabs TTS")
        raise ElevenLabsTTSError("Таймаут при запросе к ElevenLabs TTS")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к ElevenLabs TTS: {e}")
        raise ElevenLabsTTSError(f"Ошибка при запросе к ElevenLabs TTS: {e}")


async def synthesize_with_request(request: TTSRequest) -> bytes:
    """
    Синтезировать речь с использованием Pydantic модели.
    
    Args:
        request: Модель запроса к TTS
        
    Returns:
        bytes: Аудио данные
    """
    return await synthesize_elevenlabs(
        text=request.text,
        voice_id=request.voice,
        output_format=request.format
    )


async def get_voices() -> list:
    """
    Получить список доступных голосов.
    
    Returns:
        list: Список голосов
        
    Raises:
        ElevenLabsTTSError: При ошибке API
    """
    if not settings.elevenlabs_api_key:
        raise ElevenLabsTTSError("Не настроен API ключ ElevenLabs")
    
    headers = {
        "xi-api-key": settings.elevenlabs_api_key
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug("Получаем список голосов ElevenLabs")
            
            response = await client.get(
                "https://api.elevenlabs.io/v1/voices",
                headers=headers
            )
            
            response.raise_for_status()
            data = response.json()
            
            voices = data.get("voices", [])
            logger.debug(f"Получено {len(voices)} голосов от ElevenLabs")
            return voices
            
    except HTTPStatusError as e:
        logger.error(f"HTTP ошибка при получении голосов ElevenLabs: {e.response.status_code} - {e.response.text}")
        raise ElevenLabsTTSError(f"Ошибка API ElevenLabs: {e.response.status_code}")
    except TimeoutException:
        logger.error("Таймаут при получении голосов ElevenLabs")
        raise ElevenLabsTTSError("Таймаут при получении голосов ElevenLabs")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении голосов ElevenLabs: {e}")
        raise ElevenLabsTTSError(f"Ошибка при получении голосов ElevenLabs: {e}")
