"""
Тесты для роутинга TTS провайдеров и выбора send_voice vs send_audio.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User

from app.services.tts import synthesize, TTSProviderError
from app.services.tg_utils import send_voice_message, send_audio_message


@pytest.mark.asyncio
async def test_tts_facade_yandex_provider():
    """Тест фасада TTS с провайдером Yandex."""
    with patch("app.services.tts.settings.tts_provider", "yandex"), \
         patch("app.services.tts._synthesize_yandex") as mock_yandex:
        
        mock_yandex.return_value = {
            "type": "voice",
            "data": b"fake_ogg_data"
        }
        
        result = await synthesize("Тестовый текст")
        
        assert result["type"] == "voice"
        assert result["data"] == b"fake_ogg_data"
        mock_yandex.assert_called_once_with("Тестовый текст")


@pytest.mark.asyncio
async def test_tts_facade_elevenlabs_provider():
    """Тест фасада TTS с провайдером ElevenLabs."""
    with patch("app.services.tts.settings.tts_provider", "elevenlabs"), \
         patch("app.services.tts.settings.elevenlabs_convert_to_ogg", False), \
         patch("app.services.tts._synthesize_elevenlabs") as mock_elevenlabs:
        
        mock_elevenlabs.return_value = {
            "type": "audio",
            "data": b"fake_mp3_data"
        }
        
        result = await synthesize("Тестовый текст")
        
        assert result["type"] == "audio"
        assert result["data"] == b"fake_mp3_data"
        mock_elevenlabs.assert_called_once_with("Тестовый текст")


@pytest.mark.asyncio
async def test_tts_facade_elevenlabs_with_conversion():
    """Тест фасада TTS с ElevenLabs и конвертацией в OGG."""
    with patch("app.services.tts.settings.tts_provider", "elevenlabs"), \
         patch("app.services.tts.settings.elevenlabs_convert_to_ogg", True), \
         patch("app.services.tts._synthesize_elevenlabs") as mock_elevenlabs, \
         patch("app.services.tts._convert_mp3_to_ogg") as mock_convert:
        
        mock_elevenlabs.return_value = {
            "type": "audio",
            "data": b"fake_mp3_data"
        }
        mock_convert.return_value = b"fake_ogg_data"
        
        result = await synthesize("Тестовый текст")
        
        assert result["type"] == "voice"
        assert result["data"] == b"fake_ogg_data"
        mock_convert.assert_called_once_with(b"fake_mp3_data")


@pytest.mark.asyncio
async def test_tts_facade_unsupported_provider():
    """Тест фасада TTS с неподдерживаемым провайдером."""
    with patch("app.services.tts.settings.tts_provider", "unsupported"):
        with pytest.raises(TTSProviderError, match="Неподдерживаемый TTS провайдер"):
            await synthesize("Тестовый текст")


@pytest.mark.asyncio
async def test_tts_facade_provider_error():
    """Тест фасада TTS с ошибкой провайдера."""
    with patch("app.services.tts.settings.tts_provider", "yandex"), \
         patch("app.services.tts._synthesize_yandex") as mock_yandex:
        
        mock_yandex.side_effect = Exception("Provider error")
        
        with pytest.raises(TTSProviderError, match="Неожиданная ошибка TTS"):
            await synthesize("Тестовый текст")


@pytest.mark.asyncio
async def test_router_voice_vs_audio_selection():
    """Тест выбора send_voice vs send_audio в роутере."""
    # Мокаем сообщение
    mock_message = MagicMock(spec=Message)
    mock_message.from_user.id = 123
    mock_message.message_id = 456
    mock_message.text = "Тест"
    
    # Мокаем бота
    mock_bot = MagicMock()
    
    with patch("app.router.complete_text") as mock_llm, \
         patch("app.router.synthesize") as mock_tts, \
         patch("app.router.send_voice_message") as mock_send_voice, \
         patch("app.router.send_audio_message") as mock_send_audio:
        
        mock_llm.return_value = "LLM response"
        
        # Тест 1: voice формат (Yandex)
        mock_tts.return_value = {
            "type": "voice",
            "data": b"ogg_data"
        }
        
        # Имитируем обработку сообщения
        from app.router import message_handler
        await message_handler(mock_message)
        
        mock_send_voice.assert_called_once()
        mock_send_audio.assert_not_called()
        
        # Сброс моков
        mock_send_voice.reset_mock()
        mock_send_audio.reset_mock()
        
        # Тест 2: audio формат (ElevenLabs без конвертации)
        mock_tts.return_value = {
            "type": "audio",
            "data": b"mp3_data"
        }
        
        await message_handler(mock_message)
        
        mock_send_audio.assert_called_once()
        mock_send_voice.assert_not_called()
