"""
Фасад для TTS провайдеров с роутингом.
"""
import logging
import subprocess
import tempfile
from typing import Dict, Any, Union
from pathlib import Path

from app.settings import settings
from app.services.yandex_tts import synthesize_speech as yandex_synthesize, YandexTTSError
from app.services.elevenlabs_tts import synthesize_elevenlabs, ElevenLabsTTSError

logger = logging.getLogger(__name__)


class TTSProviderError(Exception):
    """Ошибка TTS провайдера."""
    pass


async def synthesize(text: str) -> Dict[str, Any]:
    """
    Синтезировать речь через выбранный провайдер.
    
    Args:
        text: Текст для синтеза
        
    Returns:
        Dict с ключами:
        - type: "voice" (oggopus) или "audio" (mp3)
        - data: bytes аудио данных
        
    Raises:
        TTSProviderError: При ошибке синтеза
    """
    provider = settings.tts_provider.lower()
    
    try:
        if provider == "yandex":
            return await _synthesize_yandex(text)
        elif provider == "elevenlabs":
            return await _synthesize_elevenlabs(text)
        else:
            raise TTSProviderError(f"Неподдерживаемый TTS провайдер: {provider}")
            
    except (YandexTTSError, ElevenLabsTTSError) as e:
        logger.error(f"Ошибка TTS провайдера {provider}: {e}")
        raise TTSProviderError(f"Ошибка TTS провайдера {provider}: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка TTS: {e}")
        raise TTSProviderError(f"Неожиданная ошибка TTS: {e}")


async def _synthesize_yandex(text: str) -> Dict[str, Any]:
    """Синтез через Yandex TTS (oggopus)."""
    logger.debug(f"Синтез через Yandex TTS: {text[:50]}...")
    
    audio_data = await yandex_synthesize(
        text=text,
        voice=settings.yandex_tts_voice,
        format=settings.yandex_tts_format
    )
    
    return {
        "type": "voice",  # oggopus для Telegram voice
        "data": audio_data
    }


async def _synthesize_elevenlabs(text: str) -> Dict[str, Any]:
    """Синтез через ElevenLabs TTS (mp3)."""
    logger.debug(f"Синтез через ElevenLabs TTS: {text[:50]}...")
    
    audio_data = await synthesize_elevenlabs(text)
    
    # Проверяем, нужно ли конвертировать в OGG/OPUS
    if settings.elevenlabs_convert_to_ogg:
        try:
            converted_data = await _convert_mp3_to_ogg(audio_data)
            return {
                "type": "voice",  # oggopus для Telegram voice
                "data": converted_data
            }
        except Exception as e:
            logger.warning(f"Ошибка конвертации MP3 в OGG: {e}, отправляем как audio")
    
    return {
        "type": "audio",  # mp3 для Telegram audio
        "data": audio_data
    }


async def _convert_mp3_to_ogg(mp3_data: bytes) -> bytes:
    """
    Конвертировать MP3 в OGG/OPUS через ffmpeg.
    
    Args:
        mp3_data: MP3 аудио данные
        
    Returns:
        bytes: OGG/OPUS аудио данные
        
    Raises:
        TTSProviderError: При ошибке конвертации
    """
    try:
        # Проверяем наличие ffmpeg
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise TTSProviderError("ffmpeg не найден. Установите ffmpeg для конвертации аудио")
    
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as mp3_file:
        mp3_file.write(mp3_data)
        mp3_path = mp3_file.name
    
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
        ogg_path = ogg_file.name
    
    try:
        # Конвертируем MP3 в OGG/OPUS
        cmd = [
            "ffmpeg",
            "-i", mp3_path,
            "-c:a", "libopus",
            "-b:a", "64k",
            "-ar", "48000",
            "-ac", "1",
            "-y",  # Перезаписать файл
            ogg_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, check=True)
        
        # Читаем конвертированный файл
        with open(ogg_path, "rb") as f:
            ogg_data = f.read()
        
        logger.debug(f"Конвертировано MP3 в OGG: {len(mp3_data)} -> {len(ogg_data)} байт")
        return ogg_data
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка ffmpeg: {e.stderr.decode()}")
        raise TTSProviderError(f"Ошибка конвертации аудио: {e.stderr.decode()}")
    finally:
        # Удаляем временные файлы
        try:
            Path(mp3_path).unlink()
            Path(ogg_path).unlink()
        except Exception as e:
            logger.warning(f"Не удалось удалить временные файлы: {e}")


def get_available_providers() -> list:
    """Получить список доступных TTS провайдеров."""
    return ["yandex", "elevenlabs"]


def get_current_provider() -> str:
    """Получить текущий TTS провайдер."""
    return settings.tts_provider


def is_voice_format(provider: str = None) -> bool:
    """
    Проверить, возвращает ли провайдер формат voice (oggopus).
    
    Args:
        provider: Провайдер для проверки (по умолчанию текущий)
        
    Returns:
        bool: True если формат voice, False если audio
    """
    provider = provider or settings.tts_provider.lower()
    
    if provider == "yandex":
        return True  # Yandex всегда возвращает oggopus
    elif provider == "elevenlabs":
        return settings.elevenlabs_convert_to_ogg  # Зависит от флага конвертации
    else:
        return False
