"""
Тесты для ElevenLabs TTS с моками httpx.
"""
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from httpx import HTTPStatusError, Response

from app.services.elevenlabs_tts import synthesize_elevenlabs, get_voices, ElevenLabsTTSError


@pytest.mark.asyncio
async def test_elevenlabs_tts_success():
    """Тест успешного запроса к ElevenLabs TTS."""
    mock_audio_data = b"fake_mp3_audio_data"
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Response(200, content=mock_audio_data)
        mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
        
        result = await synthesize_elevenlabs("Тестовый текст")
        
        assert result == mock_audio_data


@pytest.mark.asyncio
async def test_elevenlabs_tts_error():
    """Тест ошибки ElevenLabs TTS."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.post.side_effect = HTTPStatusError(
            "Bad Request", request=None, response=Response(400, text="Error")
        )
        
        with pytest.raises(ElevenLabsTTSError):
            await synthesize_elevenlabs("Тестовый текст")


@pytest.mark.asyncio
async def test_elevenlabs_tts_empty_text():
    """Тест с пустым текстом."""
    with pytest.raises(ElevenLabsTTSError, match="Пустой текст"):
        await synthesize_elevenlabs("")


@pytest.mark.asyncio
async def test_elevenlabs_tts_long_text():
    """Тест с слишком длинным текстом."""
    long_text = "a" * 5001
    
    with pytest.raises(ElevenLabsTTSError, match="слишком длинный"):
        await synthesize_elevenlabs(long_text)


@pytest.mark.asyncio
async def test_elevenlabs_get_voices_success():
    """Тест успешного получения списка голосов."""
    mock_voices_data = {
        "voices": [
            {"voice_id": "voice1", "name": "Liam"},
            {"voice_id": "voice2", "name": "Sarah"}
        ]
    }
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = Response(200, json=mock_voices_data)
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        voices = await get_voices()
        
        assert len(voices) == 2
        assert voices[0]["name"] == "Liam"


@pytest.mark.asyncio
async def test_elevenlabs_get_voices_error():
    """Тест ошибки получения голосов."""
    with patch("httpx.AsyncClient") as mock_client:
        mock_client.return_value.__aenter__.return_value.get.side_effect = HTTPStatusError(
            "Unauthorized", request=None, response=Response(401, text="Unauthorized")
        )
        
        with pytest.raises(ElevenLabsTTSError):
            await get_voices()
