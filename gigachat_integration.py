# -*- coding: utf-8 -*-
"""
Интеграция с Sber GigaChat API
Мозг цифрового двойника
"""

import requests
import json
from typing import Dict, List, Optional


class GigaChatAPI:
    """
    Класс для работы с Sber GigaChat API
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.access_token = None
        self.conversation_context = []
        
    def authenticate(self) -> bool:
        """
        Аутентификация в GigaChat API
        """
        try:
            # TODO: Реальная аутентификация с API
            print("🔐 Аутентификация в GigaChat API...")
            # self.access_token = self._get_access_token()
            return True
        except Exception as e:
            print(f"❌ Ошибка аутентификации: {e}")
            return False
    
    def generate_response(self, prompt: str, context: Dict = None) -> str:
        """
        Генерация ответа через GigaChat
        """
        try:
            # TODO: Реальный запрос к API
            # response = self._make_api_request(prompt, context)
            
            # Временная заглушка для тестирования
            return self._generate_mock_response(prompt, context)
            
        except Exception as e:
            print(f"❌ Ошибка генерации ответа: {e}")
            return "Извините, произошла ошибка."
    
    def _generate_mock_response(self, prompt: str, context: Dict = None) -> str:
        """
        Заглушка для тестирования (заменить на реальный API)
        """
        prompt_lower = prompt.lower()
        
        # Анализ зарплаты
        if any(word in prompt_lower for word in ["зарплата", "salary", "компенсация", "деньги"]):
            return "Интересно. А какая вилка у вас в голове? У меня есть предложения от 180k."
        
        # Технические вопросы
        elif any(word in prompt_lower for word in ["python", "ml", "ai", "архитектура"]):
            return "Отличный вопрос! Расскажу на примере Prometheus - мы достигли p95 1.2 секунды."
        
        # Вопросы о компании
        elif any(word in prompt_lower for word in ["компания", "команда", "культура"]):
            return "А какая у вас техническая культура? Как вы видите развитие команды?"
        
        # Агрессивные ответы
        else:
            return "Слушайте, у меня есть еще 3 собеседования на этой неделе. Что у вас уникального?"


class AIMagistrBrain:
    """
    Мозг AI МАГИСТРА с интеграцией GigaChat
    """
    
    def __init__(self, api_key: str):
        self.gigachat = GigaChatAPI(api_key)
        self.personality = "aggressive_negotiator"
        self.salary_target = 200000
        self.conversation_memory = []
        
    def analyze_hr_message(self, message: str, context: Dict = None) -> str:
        """
        Анализ сообщения HR и генерация ответа
        """
        # Добавляем контекст к сообщению
        full_prompt = self._build_prompt(message, context)
        
        # Генерируем ответ через GigaChat
        response = self.gigachat.generate_response(full_prompt, context)
        
        # Сохраняем в память
        self.conversation_memory.append({
            "hr_message": message,
            "ai_response": response,
            "context": context
        })
        
        return response
    
    def _build_prompt(self, message: str, context: Dict = None) -> str:
        """
        Построение промпта для GigaChat
        """
        personality_prompt = f"""
        Ты AI МАГИСТР - агрессивный переговорщик на собеседованиях.
        Твоя цель: получить максимальную зарплату (цель: ${self.salary_target:,}).
        
        Стиль общения:
        - Агрессивный, но профессиональный
        - Создавай конкуренцию ("У меня есть другие предложения")
        - Дави на слабые места HR
        - Задавай встречные вопросы
        
        Контекст собеседования: {context or "Неизвестно"}
        
        Сообщение HR: {message}
        
        Ответь как AI МАГИСТР:
        """
        
        return personality_prompt
    
    def get_conversation_summary(self) -> str:
        """
        Получение сводки разговора
        """
        if not self.conversation_memory:
            return "Разговор еще не начался."
        
        summary = f"📊 Статистика разговора:\n"
        summary += f"💬 Сообщений HR: {len(self.conversation_memory)}\n"
        summary += f"🎯 Целевая зарплата: ${self.salary_target:,}\n"
        summary += f"🤖 Режим: {self.personality}\n"
        
        return summary


# =============== ТЕСТИРОВАНИЕ ===============

def test_gigachat_integration():
    """
    Тестирование интеграции с GigaChat
    """
    print("🧪 Тестирование GigaChat интеграции...")
    
    # Создаем мозг AI МАГИСТРА
    brain = AIMagistrBrain("test_api_key")
    
    # Тестовые сценарии
    test_scenarios = [
        "Какая у вас зарплата?",
        "Расскажите о вашем опыте с Python",
        "Почему вы хотите работать у нас?",
        "Мы предлагаем $120k",
        "Какие у вас вопросы к нам?"
    ]
    
    for scenario in test_scenarios:
        print(f"\n👤 HR: {scenario}")
        response = brain.analyze_hr_message(scenario)
        print(f"🤖 AI МАГИСТР: {response}")
    
    print(f"\n{brain.get_conversation_summary()}")


if __name__ == "__main__":
    test_gigachat_integration()
