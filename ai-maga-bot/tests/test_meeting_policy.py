"""
Тесты для политики встреч.
"""
import pytest
from unittest.mock import AsyncMock, patch
from app.services.meeting_policy import (
    MeetingProfile, MeetingPolicy, PolicyGuard, PolicyResult, MeetingSession
)


@pytest.fixture
def meeting_policy():
    """Фикстура для политики встреч."""
    return MeetingPolicy()


@pytest.fixture
def policy_guard(meeting_policy):
    """Фикстура для стража политики."""
    return PolicyGuard(meeting_policy)


@pytest.fixture
def meeting_session():
    """Фикстура для сессии встречи."""
    return MeetingSession("test_meeting_123", MeetingProfile.NOTE_TAKER)


def test_meeting_profile_enum():
    """Тест enum профилей встреч."""
    assert MeetingProfile.SILENT.value == "silent"
    assert MeetingProfile.NOTE_TAKER.value == "note_taker"
    assert MeetingProfile.COHOST.value == "cohost"


def test_get_profile_config(meeting_policy):
    """Тест получения конфигурации профиля."""
    silent_config = meeting_policy.get_profile_config(MeetingProfile.SILENT)
    assert silent_config["ai_muted"] is True
    assert silent_config["max_reply_sec"] == 0
    
    cohost_config = meeting_policy.get_profile_config(MeetingProfile.COHOST)
    assert cohost_config["ai_muted"] is False
    assert cohost_config["max_reply_sec"] == 60


def test_get_system_prompt(meeting_policy):
    """Тест получения системного промпта."""
    silent_prompt = meeting_policy.get_system_prompt(MeetingProfile.SILENT)
    assert "молчаливый наблюдатель" in silent_prompt
    
    cohost_prompt = meeting_policy.get_system_prompt(MeetingProfile.COHOST)
    assert "соведущий встречи" in cohost_prompt


@pytest.mark.asyncio
async def test_policy_guard_silent_mode(policy_guard):
    """Тест стража политики в silent режиме."""
    result = await policy_guard.check("Любой текст", MeetingProfile.SILENT)
    
    assert result.allowed is False
    assert "AI is muted" in result.reason


@pytest.mark.asyncio
async def test_policy_guard_banned_phrases(policy_guard):
    """Тест проверки запрещенных фраз."""
    result = await policy_guard.check("Спасибо за внимание", MeetingProfile.NOTE_TAKER)
    
    assert result.allowed is False
    assert "banned phrase" in result.reason


@pytest.mark.asyncio
async def test_policy_guard_stop_words(policy_guard):
    """Тест проверки стоп-слов."""
    result = await policy_guard.check("Извините, перебиваю", MeetingProfile.NOTE_TAKER)
    
    assert result.allowed is False
    assert "stop word" in result.reason


@pytest.mark.asyncio
async def test_policy_guard_allowed_text(policy_guard):
    """Тест разрешенного текста."""
    result = await policy_guard.check("Можете уточнить детали?", MeetingProfile.NOTE_TAKER)
    
    assert result.allowed is True
    assert result.reason == "Text approved by policy"


@pytest.mark.asyncio
async def test_policy_guard_llm_classification(policy_guard):
    """Тест LLM классификации."""
    with patch('app.settings.settings') as mock_settings:
        mock_settings.llm_provider = "yandex"
        
        with patch('app.services.yandex_llm.complete_text') as mock_llm:
            mock_llm.return_value = '{"allowed": true, "reason": "LLM approved"}'
            
            result = await policy_guard.check("Вопрос по повестке", MeetingProfile.COHOST)
            
            assert result.allowed is True
            assert "LLM approved" in result.reason


@pytest.mark.asyncio
async def test_policy_guard_llm_rejection(policy_guard):
    """Тест LLM отклонения."""
    with patch('app.settings.settings') as mock_settings:
        mock_settings.llm_provider = "yandex"
        
        with patch('app.services.yandex_llm.complete_text') as mock_llm:
            mock_llm.return_value = '{"allowed": false, "reason": "Inappropriate content"}'
            
            result = await policy_guard.check("Неподходящий контент", MeetingProfile.COHOST)
            
            assert result.allowed is False
            assert "LLM classification failed" in result.reason


@pytest.mark.asyncio
async def test_policy_guard_llm_fallback(policy_guard):
    """Тест fallback при ошибке LLM."""
    with patch('app.settings.settings') as mock_settings:
        mock_settings.llm_provider = "yandex"
        
        with patch('app.services.yandex_llm.complete_text') as mock_llm:
            mock_llm.side_effect = Exception("LLM unavailable")
            
            result = await policy_guard.check("Обычный текст", MeetingProfile.COHOST)
            
            # При ошибке LLM должен разрешить (fail-open)
            assert result.allowed is True
            assert "LLM unavailable" in result.reason


def test_meeting_session_creation(meeting_session):
    """Тест создания сессии встречи."""
    assert meeting_session.meeting_id == "test_meeting_123"
    assert meeting_session.profile == MeetingProfile.NOTE_TAKER
    assert meeting_session.ai_muted is False  # NOTE_TAKER не заглушен по умолчанию


def test_meeting_session_mute_unmute(meeting_session):
    """Тест заглушения/включения ИИ."""
    assert meeting_session.ai_muted is False
    
    meeting_session.mute_ai()
    assert meeting_session.ai_muted is True
    
    meeting_session.unmute_ai()
    assert meeting_session.ai_muted is False


def test_meeting_session_set_profile(meeting_session):
    """Тест изменения профиля."""
    assert meeting_session.profile == MeetingProfile.NOTE_TAKER
    
    meeting_session.set_profile(MeetingProfile.SILENT)
    assert meeting_session.profile == MeetingProfile.SILENT
    assert meeting_session.ai_muted is True  # SILENT профиль заглушен


@pytest.mark.asyncio
async def test_meeting_session_check_message(meeting_session):
    """Тест проверки сообщения через сессию."""
    with patch.object(meeting_session.guard, 'check') as mock_check:
        mock_check.return_value = PolicyResult(allowed=True, reason="OK")
        
        result = await meeting_session.check_message("Тестовое сообщение")
        
        assert result.allowed is True
        mock_check.assert_called_once_with("Тестовое сообщение", MeetingProfile.NOTE_TAKER)


def test_policy_result_creation():
    """Тест создания результата политики."""
    result = PolicyResult(
        allowed=True,
        reason="Text approved",
        edited_text="Edited version"
    )
    
    assert result.allowed is True
    assert result.reason == "Text approved"
    assert result.edited_text == "Edited version"


def test_policy_result_rejection():
    """Тест результата отклонения."""
    result = PolicyResult(
        allowed=False,
        reason="Contains banned phrase"
    )
    
    assert result.allowed is False
    assert result.reason == "Contains banned phrase"
    assert result.edited_text is None
