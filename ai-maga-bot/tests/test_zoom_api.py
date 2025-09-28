"""
Тесты для Zoom API клиента.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from app.services.zoom_api import ZoomAPIClient


@pytest.fixture
def zoom_client():
    """Фикстура для Zoom клиента."""
    with patch('app.settings.settings') as mock_settings:
        mock_settings.zoom_account_id = "test_account"
        mock_settings.zoom_client_id = "test_client"
        mock_settings.zoom_client_secret = "test_secret"
        mock_settings.zoom_default_user = "me"
        
        client = ZoomAPIClient()
        return client


@pytest.mark.asyncio
async def test_get_access_token_success(zoom_client):
    """Тест успешного получения access token."""
    mock_response = {
        "access_token": "test_token",
        "expires_in": 3600,
        "token_type": "Bearer"
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 200
        mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response
        
        token = await zoom_client._get_access_token()
        
        assert token == "test_token"
        assert zoom_client._access_token == "test_token"


@pytest.mark.asyncio
async def test_get_access_token_failure(zoom_client):
    """Тест неудачного получения access token."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post.return_value.status_code = 401
        mock_client.return_value.__aenter__.return_value.post.return_value.text = "Unauthorized"
        
        with pytest.raises(Exception, match="Failed to get access token"):
            await zoom_client._get_access_token()


@pytest.mark.asyncio
async def test_list_meetings(zoom_client):
    """Тест получения списка встреч."""
    mock_meetings = [
        {"id": "123", "topic": "Test Meeting 1"},
        {"id": "456", "topic": "Test Meeting 2"}
    ]
    mock_response = {"meetings": mock_meetings}
    
    with patch.object(zoom_client, '_make_request', return_value=mock_response):
        meetings = await zoom_client.list_meetings("test_user")
        
        assert len(meetings) == 2
        assert meetings[0]["id"] == "123"
        assert meetings[1]["topic"] == "Test Meeting 2"


@pytest.mark.asyncio
async def test_create_meeting(zoom_client):
    """Тест создания встречи."""
    mock_meeting = {
        "id": "789",
        "topic": "New Meeting",
        "join_url": "https://zoom.us/j/789",
        "password": "123456"
    }
    
    with patch.object(zoom_client, '_make_request', return_value=mock_meeting):
        meeting = await zoom_client.create_meeting("Test Topic", duration=60)
        
        assert meeting["id"] == "789"
        assert meeting["topic"] == "New Meeting"
        assert meeting["join_url"] == "https://zoom.us/j/789"


@pytest.mark.asyncio
async def test_get_meeting(zoom_client):
    """Тест получения информации о встрече."""
    mock_meeting = {
        "id": "123",
        "topic": "Test Meeting",
        "start_time": "2024-01-01T10:00:00Z",
        "duration": 60
    }
    
    with patch.object(zoom_client, '_make_request', return_value=mock_meeting):
        meeting = await zoom_client.get_meeting("123")
        
        assert meeting["id"] == "123"
        assert meeting["topic"] == "Test Meeting"


@pytest.mark.asyncio
async def test_join_meeting(zoom_client):
    """Тест получения ссылки для присоединения к встрече."""
    mock_meeting = {
        "id": "123",
        "join_url": "https://zoom.us/j/123",
        "password": "testpass"
    }
    
    with patch.object(zoom_client, 'get_meeting', return_value=mock_meeting):
        join_info = await zoom_client.join_meeting("123", "testpass")
        
        assert join_info["meeting_id"] == "123"
        assert "testpass" in join_info["join_url"]
        assert join_info["password"] == "testpass"


@pytest.mark.asyncio
async def test_get_transcript_success(zoom_client):
    """Тест успешного получения стенограммы."""
    mock_transcript = "Speaker 1: Hello everyone. Speaker 2: Good morning."
    
    with patch.object(zoom_client, '_make_request', return_value={"transcript": mock_transcript}):
        transcript = await zoom_client.get_transcript("123")
        
        assert transcript == mock_transcript


@pytest.mark.asyncio
async def test_get_transcript_not_found(zoom_client):
    """Тест получения стенограммы когда её нет."""
    with patch.object(zoom_client, '_make_request', side_effect=Exception("No transcript")):
        transcript = await zoom_client.get_transcript("123")
        
        assert transcript is None


@pytest.mark.asyncio
async def test_get_recording_files(zoom_client):
    """Тест получения файлов записи."""
    mock_files = [
        {"id": "file1", "file_type": "MP4", "file_size": 1024000},
        {"id": "file2", "file_type": "M4A", "file_size": 512000}
    ]
    
    with patch.object(zoom_client, '_make_request', return_value={"recording_files": mock_files}):
        files = await zoom_client.get_recording_files("123")
        
        assert len(files) == 2
        assert files[0]["file_type"] == "MP4"
        assert files[1]["file_size"] == 512000


@pytest.mark.asyncio
async def test_make_request_with_token_refresh(zoom_client):
    """Тест выполнения запроса с обновлением токена."""
    # Первый запрос возвращает 401, второй - успех
    mock_responses = [
        httpx.Response(401, json={"error": "Unauthorized"}),
        httpx.Response(200, json={"data": "success"})
    ]
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.request.side_effect = mock_responses
        with patch.object(zoom_client, '_get_access_token', return_value="new_token"):
            result = await zoom_client._make_request("GET", "/test")
            
            assert result == {"data": "success"}


@pytest.mark.asyncio
async def test_make_request_api_error(zoom_client):
    """Тест обработки ошибки API."""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.request.return_value.status_code = 400
        mock_client.return_value.__aenter__.return_value.request.return_value.text = "Bad Request"
        
        with pytest.raises(Exception, match="Zoom API error"):
            await zoom_client._make_request("GET", "/test")
