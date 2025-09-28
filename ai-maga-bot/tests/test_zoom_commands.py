"""
Тесты для Zoom команд в Telegram боте.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiogram.types import Message, User
from app.router import zoom_handler


@pytest.fixture
def mock_message():
    """Фикстура для сообщения Telegram."""
    user = User(id=12345, is_bot=False, first_name="Test", username="testuser")
    message = MagicMock(spec=Message)
    message.from_user = user
    message.text = "/zoom"
    return message


@pytest.fixture
def mock_orchestrator():
    """Фикстура для оркестратора."""
    orchestrator = AsyncMock()
    return orchestrator


@pytest.mark.asyncio
async def test_zoom_help_command(mock_message):
    """Тест команды /zoom без параметров (справка)."""
    with patch('app.router.send_text_message') as mock_send:
        await zoom_handler(mock_message)
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert "Zoom команды:" in call_args[1]
        assert "/zoom join" in call_args[1]
        assert "/zoom create" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_join_success(mock_message, mock_orchestrator):
    """Тест успешного присоединения к встрече."""
    mock_message.text = "/zoom join 123456789 password123"
    
    mock_orchestrator.zoom_join_meeting.return_value = {
        "status": "success",
        "data": {
            "join_url": "https://zoom.us/j/123456789",
            "meeting_id": "123456789",
            "password": "password123"
        }
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_orchestrator.zoom_join_meeting.assert_called_once_with(12345, "123456789", "password123")
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Ссылка для присоединения:" in call_args[1]
            assert "123456789" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_join_without_password(mock_message, mock_orchestrator):
    """Тест присоединения к встрече без пароля."""
    mock_message.text = "/zoom join 123456789"
    
    mock_orchestrator.zoom_join_meeting.return_value = {
        "status": "success",
        "data": {
            "join_url": "https://zoom.us/j/123456789",
            "meeting_id": "123456789",
            "password": ""
        }
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_orchestrator.zoom_join_meeting.assert_called_once_with(12345, "123456789", None)


@pytest.mark.asyncio
async def test_zoom_join_error(mock_message, mock_orchestrator):
    """Тест ошибки присоединения к встрече."""
    mock_message.text = "/zoom join 123456789"
    
    mock_orchestrator.zoom_join_meeting.return_value = {
        "status": "error",
        "message": "Meeting not found"
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Ошибка: Meeting not found" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_create_success(mock_message, mock_orchestrator):
    """Тест успешного создания встречи."""
    mock_message.text = "/zoom create Test Meeting Topic"
    
    mock_orchestrator.zoom_create_meeting.return_value = {
        "status": "success",
        "data": {
            "id": "987654321",
            "topic": "Test Meeting Topic",
            "join_url": "https://zoom.us/j/987654321",
            "password": "testpass"
        }
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_orchestrator.zoom_create_meeting.assert_called_once_with(12345, "Test Meeting Topic")
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Встреча создана!" in call_args[1]
            assert "987654321" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_mode_success(mock_message, mock_orchestrator):
    """Тест успешной смены режима ИИ."""
    mock_message.text = "/zoom mode 123456789 cohost"
    
    mock_orchestrator.zoom_set_meeting_mode.return_value = {
        "status": "success",
        "mode": "cohost"
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_orchestrator.zoom_set_meeting_mode.assert_called_once_with(12345, "123456789", "cohost")
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Режим ИИ изменен на: cohost" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_mode_invalid_mode(mock_message, mock_orchestrator):
    """Тест неверного режима ИИ."""
    mock_message.text = "/zoom mode 123456789 invalid_mode"
    
    mock_orchestrator.zoom_set_meeting_mode.return_value = {
        "status": "error",
        "message": "Invalid mode: invalid_mode"
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Ошибка: Invalid mode: invalid_mode" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_mute_success(mock_message, mock_orchestrator):
    """Тест успешного заглушения ИИ."""
    mock_message.text = "/zoom mute 123456789"
    
    mock_orchestrator.zoom_mute_ai.return_value = {
        "status": "success",
        "muted": True
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_orchestrator.zoom_mute_ai.assert_called_once_with(12345, "123456789")
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "ИИ заглушен на встрече" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_status_specific_meeting(mock_message, mock_orchestrator):
    """Тест получения статуса конкретной встречи."""
    mock_message.text = "/zoom status 123456789"
    
    mock_orchestrator.zoom_get_status.return_value = {
        "status": "success",
        "meeting_id": "123456789",
        "profile": "note_taker",
        "ai_muted": False,
        "start_time": "2024-01-01T10:00:00"
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_orchestrator.zoom_get_status.assert_called_once_with(12345, "123456789")
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Статус встречи 123456789:" in call_args[1]
            assert "note_taker" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_status_all_meetings(mock_message, mock_orchestrator):
    """Тест получения статуса всех встреч."""
    mock_message.text = "/zoom status"
    
    mock_orchestrator.zoom_get_status.return_value = {
        "status": "success",
        "active_meetings": [
            {
                "meeting_id": "111",
                "profile": "cohost",
                "ai_muted": False,
                "start_time": "2024-01-01T10:00:00"
            },
            {
                "meeting_id": "222",
                "profile": "silent",
                "ai_muted": True,
                "start_time": "2024-01-01T11:00:00"
            }
        ]
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_orchestrator.zoom_get_status.assert_called_once_with(12345, None)
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Активные встречи:" in call_args[1]
            assert "111" in call_args[1]
            assert "222" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_status_no_meetings(mock_message, mock_orchestrator):
    """Тест статуса когда нет активных встреч."""
    mock_message.text = "/zoom status"
    
    mock_orchestrator.zoom_get_status.return_value = {
        "status": "success",
        "active_meetings": []
    }
    
    with patch('app.router.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.router.send_text_message') as mock_send:
            await zoom_handler(mock_message)
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            assert "Нет активных встреч" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_unknown_command(mock_message):
    """Тест неизвестной команды."""
    mock_message.text = "/zoom unknown_command"
    
    with patch('app.router.send_text_message') as mock_send:
        await zoom_handler(mock_message)
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert "Неизвестная команда" in call_args[1]


@pytest.mark.asyncio
async def test_zoom_command_error_handling(mock_message):
    """Тест обработки ошибок в командах."""
    mock_message.text = "/zoom join 123456789"
    
    with patch('app.router.get_orchestrator', side_effect=Exception("Database error")):
        with patch('app.router.send_error_message') as mock_send_error:
            await zoom_handler(mock_message)
            
            mock_send_error.assert_called_once()
            call_args = mock_send_error.call_args[0]
            assert "ошибка при обработке команды Zoom" in call_args[1]
