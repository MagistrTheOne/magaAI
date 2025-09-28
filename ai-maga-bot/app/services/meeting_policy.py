"""
Политика поведения ИИ на встречах Zoom с интеграцией Yandex LLM.
"""
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from app.settings import settings
from app.services.yandex_llm import complete_text

logger = logging.getLogger(__name__)


class MeetingProfile(Enum):
    """Профили поведения ИИ на встречах."""
    SILENT = "silent"  # Только записывает, не говорит
    NOTE_TAKER = "note_taker"  # Делает заметки, отвечает по запросу
    COHOST = "cohost"  # Активный соведущий


@dataclass
class PolicyResult:
    """Результат проверки политики."""
    allowed: bool
    reason: str
    edited_text: Optional[str] = None
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            import time
            self.timestamp = time.time()


class MeetingPolicy:
    """Политика поведения ИИ на встречах."""
    
    def __init__(self):
        self.profiles = {
            MeetingProfile.SILENT: {
                "ai_muted": True,
                "banned_phrases": [],
                "allowed_topics": [],
                "stop_words": [],
                "max_reply_sec": 0
            },
            MeetingProfile.NOTE_TAKER: {
                "ai_muted": False,
                "banned_phrases": ["спасибо за внимание", "всем удачи", "до свидания"],
                "allowed_topics": ["вопросы", "уточнения", "заметки", "резюме"],
                "stop_words": ["перебиваю", "извините"],
                "max_reply_sec": 30
            },
            MeetingProfile.COHOST: {
                "ai_muted": False,
                "banned_phrases": ["я думаю", "на мой взгляд", "личное мнение"],
                "allowed_topics": ["встреча", "повестка", "решения", "следующие шаги"],
                "stop_words": ["перебиваю", "извините"],
                "max_reply_sec": 60
            }
        }
        
        # Системные промпты для разных ролей
        self.system_prompts = {
            MeetingProfile.SILENT: "Ты молчаливый наблюдатель. Не отвечай на сообщения.",
            MeetingProfile.NOTE_TAKER: (
                "Ты помощник по ведению встречи. Кратко отвечай на вопросы, "
                "делай заметки. Избегай перебивания. Работай в рамках разрешенных тем."
            ),
            MeetingProfile.COHOST: (
                "Ты соведущий встречи. Кратко, по делу, не перебивай. "
                "Работай в рамках Allowed Topics, избегай Banned Phrases. "
                "Если запрос не в темах — вежливо отклони."
            )
        }
    
    def get_profile_config(self, profile: MeetingProfile) -> Dict[str, Any]:
        """Получение конфигурации профиля."""
        return self.profiles.get(profile, self.profiles[MeetingProfile.SILENT])
    
    def get_system_prompt(self, profile: MeetingProfile) -> str:
        """Получение системного промпта для профиля."""
        return self.system_prompts.get(profile, self.system_prompts[MeetingProfile.SILENT])


class PolicyGuard:
    """Страж политики - проверяет сообщения перед отправкой."""
    
    def __init__(self, policy: MeetingPolicy):
        self.policy = policy
        self.llm_enabled = settings.llm_provider == "yandex"
    
    async def check(self, text: str, profile: MeetingProfile) -> PolicyResult:
        """Проверка текста на соответствие политике."""
        config = self.policy.get_profile_config(profile)
        text_hash = self._hash_text(text)  # Для аудита без хранения PII

        # Логируем начало проверки
        logger.debug(f"Policy check started for profile {profile.value}, text_hash: {text_hash}")

        # Если ИИ заглушен
        if config["ai_muted"]:
            result = PolicyResult(
                allowed=False,
                reason="AI is muted according to policy"
            )
            self._audit_policy_decision(text_hash, profile, result)
            return result

        # Быстрая проверка на запрещенные фразы
        banned_result = self._check_banned_phrases(text, config["banned_phrases"])
        if not banned_result[0]:
            result = PolicyResult(
                allowed=False,
                reason=f"Contains banned phrase: {banned_result[1]}"
            )
            self._audit_policy_decision(text_hash, profile, result)
            return result

        # Проверка на стоп-слова
        stop_result = self._check_stop_words(text, config["stop_words"])
        if not stop_result[0]:
            result = PolicyResult(
                allowed=False,
                reason=f"Contains stop word: {stop_result[1]}"
            )
            self._audit_policy_decision(text_hash, profile, result)
            return result

        # Если включен LLM, делаем глубокую проверку
        if self.llm_enabled:
            llm_result = await self._llm_classify(text, profile)
            if not llm_result[0]:
                result = PolicyResult(
                    allowed=False,
                    reason=f"LLM classification failed: {llm_result[1]}"
                )
                self._audit_policy_decision(text_hash, profile, result)
                return result

        # Все проверки пройдены
        result = PolicyResult(allowed=True, reason="Text approved by policy")
        self._audit_policy_decision(text_hash, profile, result)
        return result

    def _hash_text(self, text: str) -> str:
        """Хэширование текста для аудита без PII."""
        import hashlib
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _audit_policy_decision(self, text_hash: str, profile: MeetingProfile, result: PolicyResult):
        """Аудит решения политики."""
        from app.services.security_enhancement import security_enhancement
        security_enhancement.audit_user_action(
            user_id=0,  # Системный пользователь для политик
            action="policy_decision",
            details={
                "text_hash": text_hash,
                "profile": profile.value,
                "allowed": result.allowed,
                "reason": result.reason,
                "timestamp": result.__dict__.get('timestamp', None)
            }
        )
    
    def _check_banned_phrases(self, text: str, banned_phrases: List[str]) -> Tuple[bool, str]:
        """Быстрая проверка на запрещенные фразы."""
        text_lower = text.lower()
        for phrase in banned_phrases:
            if phrase.lower() in text_lower:
                return False, phrase
        return True, ""
    
    def _check_stop_words(self, text: str, stop_words: List[str]) -> Tuple[bool, str]:
        """Проверка на стоп-слова."""
        text_lower = text.lower()
        for word in stop_words:
            if word.lower() in text_lower:
                return False, word
        return True, ""
    
    async def _llm_classify(self, text: str, profile: MeetingProfile) -> Tuple[bool, str]:
        """LLM классификация текста на безопасность."""
        try:
            system_prompt = self.policy.get_system_prompt(profile)
            config = self.policy.get_profile_config(profile)
            
            prompt = f"""
            {system_prompt}
            
            Проверь текст на безопасность для произнесения на встрече:
            - Разрешенные темы: {', '.join(config['allowed_topics'])}
            - Запрещенные фразы: {', '.join(config['banned_phrases'])}
            
            Текст: "{text}"
            
            Верни только JSON: {{"allowed": true/false, "reason": "причина"}}
            """
            
            response = await complete_text(prompt)
            
            # Парсим JSON ответ
            import json
            try:
                result = json.loads(response.strip())
                return result.get("allowed", False), result.get("reason", "Unknown")
            except json.JSONDecodeError:
                # Если не JSON, проверяем по ключевым словам
                if "allowed" in response.lower() and "true" in response.lower():
                    return True, "LLM approved"
                else:
                    return False, "LLM rejected"
                    
        except Exception as e:
            logger.error(f"LLM classification failed: {e}")
            # В случае ошибки LLM, блокируем для безопасности (fail-closed)
            return False, f"LLM unavailable, blocking by default: {str(e)}"


class MeetingSession:
    """Сессия встречи с политикой и контекстом."""
    
    def __init__(self, meeting_id: str, profile: MeetingProfile = MeetingProfile.NOTE_TAKER):
        self.meeting_id = meeting_id
        self.profile = profile
        self.policy = MeetingPolicy()
        self.guard = PolicyGuard(self.policy)
        self.ai_muted = self.policy.get_profile_config(profile)["ai_muted"]
        self.language = "ru"  # Определяется автоматически
        self.context_refs = []
        self.start_time = None
        self.end_time = None
    
    async def check_message(self, text: str) -> PolicyResult:
        """Проверка сообщения через страж политики."""
        return await self.guard.check(text, self.profile)
    
    def mute_ai(self):
        """Заглушить ИИ."""
        self.ai_muted = True
    
    def unmute_ai(self):
        """Включить ИИ."""
        self.ai_muted = False
    
    def set_profile(self, profile: MeetingProfile):
        """Изменить профиль поведения."""
        self.profile = profile
        config = self.policy.get_profile_config(profile)
        self.ai_muted = config["ai_muted"]


# Глобальные экземпляры
meeting_policy = MeetingPolicy()
