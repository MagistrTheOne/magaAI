"""Tests for Yandex LLM and TTS clients."""

import pytest
from unittest.mock import AsyncMock, patch
import httpx
from app.services.yandex_llm import complete_text, YandexLLMError
from app.services.yandex_tts import synthesize_speech, YandexTTSError


class TestYandexLLM:
    """Tests for Yandex LLM service."""

    @pytest.mark.asyncio
    async def test_complete_text_success(self):
        """Test successful text completion."""
        mock_response_data = {
            "result": {
                "alternatives": [
                    {"message": {"text": "Hello, world!"}}
                ]
            }
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await complete_text(
                system_prompt="You are a helpful assistant.",
                user_message="Hello"
            )

            assert result == "Hello, world!"
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_text_api_error(self):
        """Test API error handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPError("API Error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(YandexLLMError):
                await complete_text(user_message="Hello")

    @pytest.mark.asyncio
    async def test_complete_text_invalid_response(self):
        """Test invalid response format handling."""
        mock_response_data = {"invalid": "response"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(YandexLLMError):
                await complete_text(user_message="Hello")


class TestYandexTTS:
    """Tests for Yandex TTS service."""

    @pytest.mark.asyncio
    async def test_synthesize_speech_success(self):
        """Test successful speech synthesis."""
        audio_data = b"fake_audio_data"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.content = audio_data
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await synthesize_speech(text="Hello world")

            assert result == audio_data
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_synthesize_speech_api_error(self):
        """Test API error handling."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.HTTPError("API Error")
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(YandexTTSError):
                await synthesize_speech(text="Hello world")

    @pytest.mark.asyncio
    async def test_synthesize_speech_with_custom_voice(self):
        """Test synthesis with custom voice."""
        audio_data = b"fake_audio_data"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.content = audio_data
            mock_response.raise_for_status.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await synthesize_speech(
                text="Hello world",
                voice="oksana",
                format="mp3"
            )

            assert result == audio_data

            # Check that custom parameters were used
            call_args = mock_client.post.call_args
            data = call_args[1]["data"]
            assert data["voice"] == "oksana"
            assert data["format"] == "mp3"