"""
Логика режимов ответа и хранение настроек пользователей.
"""
import logging
import re
from typing import Dict, Literal, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class UserMode:
    """Режим ответа пользователя."""
    mode: Literal["auto", "text", "voice"]
    user_id: int


class ModeManager:
    """Менеджер режимов ответа пользователей."""
    
    def __init__(self):
        # In-memory хранилище режимов (для MVP)
        # В продакшене можно заменить на Redis
        self._user_modes: Dict[int, Literal["auto", "text", "voice"]] = {}
    
    def get_user_mode(self, user_id: int) -> Literal["auto", "text", "voice"]:
        """
        Получить режим пользователя.
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Режим пользователя (по умолчанию "auto")
        """
        return self._user_modes.get(user_id, "auto")
    
    def set_user_mode(self, user_id: int, mode: Literal["auto", "text", "voice"]) -> None:
        """
        Установить режим пользователя.
        
        Args:
            user_id: ID пользователя
            mode: Новый режим
        """
        self._user_modes[user_id] = mode
        logger.info(f"Пользователь {user_id} установил режим: {mode}")
    
    def determine_response_mode(
        self, 
        user_id: int, 
        input_type: Literal["text", "voice"], 
        text_content: Optional[str] = None
    ) -> Literal["text", "voice"]:
        """
        Определить режим ответа на основе настроек пользователя и типа ввода.
        
        Args:
            user_id: ID пользователя
            input_type: Тип входящего сообщения
            text_content: Содержимое текстового сообщения (если есть)
            
        Returns:
            Режим ответа ("text" или "voice")
        """
        user_mode = self.get_user_mode(user_id)
        
        # Если пользователь явно указал режим
        if user_mode == "text":
            return "text"
        elif user_mode == "voice":
            return "voice"
        
        # Auto-режим: определяем по контексту
        if input_type == "voice":
            # Голосовое сообщение → отвечаем голосом
            return "voice"
        
        if text_content:
            # Проверяем маркеры в тексте
            voice_markers = [
                "voice", "/voice", "голос", "говори", "скажи"
            ]
            
            text_lower = text_content.lower()
            for marker in voice_markers:
                if marker.lower() in text_lower:
                    logger.debug(f"Найден маркер голоса '{marker}' в тексте")
                    return "voice"
        
        # По умолчанию текстовый ответ
        return "text"
    
    def get_mode_description(self, mode: Literal["auto", "text", "voice"]) -> str:
        """
        Получить описание режима.
        
        Args:
            mode: Режим
            
        Returns:
            Описание режима
        """
        descriptions = {
            "auto": "Автоматический (голос → голос, текст → текст, с маркерами voice → голос)",
            "text": "Всегда текстовые ответы",
            "voice": "Всегда голосовые ответы"
        }
        return descriptions.get(mode, "Неизвестный режим")


# Глобальный экземпляр менеджера режимов
mode_manager = ModeManager()


def get_user_mode(user_id: int) -> Literal["auto", "text", "voice"]:
    """Получить режим пользователя."""
    return mode_manager.get_user_mode(user_id)


def set_user_mode(user_id: int, mode: Literal["auto", "text", "voice"]) -> None:
    """Установить режим пользователя."""
    mode_manager.set_user_mode(user_id, mode)


def determine_response_mode(
    user_id: int, 
    input_type: Literal["text", "voice"], 
    text_content: Optional[str] = None
) -> Literal["text", "voice"]:
    """Определить режим ответа."""
    return mode_manager.determine_response_mode(user_id, input_type, text_content)


def get_mode_description(mode: Literal["auto", "text", "voice"]) -> str:
    """Получить описание режима."""
    return mode_manager.get_mode_description(mode)
