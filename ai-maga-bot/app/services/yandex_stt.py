"""
Сервис для работы с Yandex SpeechKit STT (опционально).
"""
import logging
from typing import Optional
import httpx
from httpx import HTTPStatusError, TimeoutException

from app.settings import settings
from app.schemas import STTRequest

logger = logging.getLogger(__name__)


class YandexSTTError(Exception):
    """Ошибка при работе с Yandex STT."""
    """Yandex SpeechKit STT провайдер."""
    pass


async def recognize_speech(
    audio_data: bytes,
    format: str = "oggopus",
    language: str = "ru-RU"
) -> str:
    """
    Распознать речь через Yandex SpeechKit STT.
    
    Args:
        audio_data: Аудио данные
        format: Формат аудио
        language: Язык распознавания
        
    Returns:
        str: Распознанный текст
        
    Raises:
        YandexSTTError: При ошибке API или сети
    """
    if not audio_data:
        raise YandexSTTError("Пустые аудио данные")
    
    if not settings.yandex_stt_enable:
        raise YandexSTTError("STT отключен в настройках")
    
    files = {
        "audio": ("audio.ogg", audio_data, "audio/ogg")
    }
    
    data = {
        "format": format,
        "language": language
    }
    
    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            logger.debug(f"Отправляем запрос к Yandex STT: {len(audio_data)} байт")
            
            response = await client.post(
                "https://stt.api.cloud.yandex.net/speech/v1/stt:recognize",
                headers=headers,
                data=data,
                files=files
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "result" in result and "alternatives" in result["result"]:
                alternatives = result["result"]["alternatives"]
                if alternatives and len(alternatives) > 0:
                    text = alternatives[0].get("text", "").strip()
                    if text:
                        logger.debug(f"Распознан текст: {text[:100]}...")
                        return text
                    else:
                        raise YandexSTTError("Пустой распознанный текст")
                else:
                    raise YandexSTTError("Нет альтернативных результатов распознавания")
            else:
                raise YandexSTTError(f"Неожиданная структура ответа STT: {result}")
                
    except HTTPStatusError as e:
        logger.error(f"HTTP ошибка при запросе к Yandex STT: {e.response.status_code} - {e.response.text}")
        raise YandexSTTError(f"Ошибка API Yandex STT: {e.response.status_code}")
    except TimeoutException:
        logger.error("Таймаут при запросе к Yandex STT")
        raise YandexSTTError("Таймаут при запросе к Yandex STT")
    except Exception as e:
        logger.error(f"Неожиданная ошибка при запросе к Yandex STT: {e}")
        raise YandexSTTError(f"Ошибка при запросе к Yandex STT: {e}")


async def recognize_with_request(request: STTRequest) -> str:
    """
    Распознать речь с использованием Pydantic модели.
    
    Args:
        request: Модель запроса к STT
        
    Returns:
        str: Распознанный текст
    """
    return await recognize_speech(
        audio_data=request.audio_data,
        format=request.format,
        language=request.language
    )
