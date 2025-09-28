"""
Тесты для Yandex API клиентов с моками httpx.
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from httpx import HTTPStatusError, Response

from app.services.yandex_llm import complete_text, YandexLLMError
from app.services.yandex_tts import synthesize_speech, YandexTTSError
from app.services.yandex_stt import recognize_speech, YandexSTTError


@pytest.mark.asyncio
async def test_yandex_llm_success():
    """Тест успешного запроса к Yandex LLM."""
    mock_response_data = {
        "result": {
            "alternatives": [
                {
                    "message": {
                        "text": "Тестовый ответ от LLM"
                    }
                }
            ]
        }
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Response(200, json=mock_response_data)
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await complete_text("Тест", "Привет")
        
        assert result == "Тестовый ответ от LLM"


@pytest.mark.asyncio
async def test_yandex_llm_error():
    """Тест ошибки Yandex LLM."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = HTTPStatusError(
            "Bad Request", request=None, response=Response(400, text="Error")
        )
        
        with pytest.raises(YandexLLMError):
            await complete_text("Тест", "Привет")


@pytest.mark.asyncio
async def test_yandex_tts_success():
    """Тест успешного запроса к Yandex TTS."""
    mock_audio_data = b"fake_audio_data"
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Response(200, content=mock_audio_data)
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await synthesize_speech("Тестовый текст")
        
        assert result == mock_audio_data


@pytest.mark.asyncio
async def test_yandex_tts_error():
    """Тест ошибки Yandex TTS."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = HTTPStatusError(
            "Bad Request", request=None, response=Response(400, text="Error")
        )
        
        with pytest.raises(YandexTTSError):
            await synthesize_speech("Тестовый текст")


@pytest.mark.asyncio
async def test_yandex_stt_success():
    """Тест успешного запроса к Yandex STT."""
    mock_response_data = {
        "result": {
            "alternatives": [
                {
                    "text": "Распознанный текст"
                }
            ]
        }
    }
    
    with patch("httpx.AsyncClient") as mock_client, \
         patch("app.settings.settings.yandex_stt_enable", True):
        mock_response = Response(200, json=mock_response_data)
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await recognize_speech(b"fake_audio_data")
        
        assert result == "Распознанный текст"


@pytest.mark.asyncio
async def test_yandex_stt_disabled():
    """Тест отключенного STT."""
    with patch("app.settings.settings.yandex_stt_enable", False):
        with pytest.raises(YandexSTTError, match="STT отключен"):
            await recognize_speech(b"fake_audio_data")


@pytest.mark.asyncio
async def test_yandex_stt_error():
    """Тест ошибки Yandex STT."""
    with patch("httpx.AsyncClient") as mock_client, \
         patch("app.settings.settings.yandex_stt_enable", True):
        mock_client.return_value.__aenter__.return_value.post.side_effect = HTTPStatusError(
            "Bad Request", request=None, response=Response(400, text="Error")
        )
        
        with pytest.raises(YandexSTTError):
            await recognize_speech(b"fake_audio_data")
