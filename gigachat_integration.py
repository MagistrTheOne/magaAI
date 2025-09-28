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
            print("🔐 Аутентификация в GigaChat API...")
            
            # Получаем токен доступа
            auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
            auth_data = {
                "scope": "GIGACHAT_API_PERS"
            }
            
            response = requests.post(
                auth_url,
                data=auth_data,
                auth=(self.api_key, ""),
                verify=False  # Для тестирования
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                print("✅ Аутентификация успешна")
                return True
            else:
                print(f"❌ Ошибка аутентификации: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка аутентификации: {e}")
            return False
    
    def generate_response(self, prompt: str, context: Dict = None) -> str:
        """
        Генерация ответа через GigaChat
        """
        try:
            if not self.access_token:
                if not self.authenticate():
                    return "Ошибка аутентификации с GigaChat API"
            
            # Реальный запрос к API
            response = self._make_api_request(prompt, context)
            return response
            
        except Exception as e:
            print(f"❌ Ошибка генерации ответа: {e}")
            # Fallback на mock если API недоступен
            return self._generate_mock_response(prompt, context)
    
    def _make_api_request(self, prompt: str, context: Dict = None) -> str:
        """
        Реальный запрос к GigaChat API
        """
        try:
            url = f"{self.base_url}/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            # Формируем сообщения для API
            messages = []
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Контекст: {context}"
                })
            
            messages.append({
                "role": "user", 
                "content": prompt
            })
            
            data = {
                "model": "GigaChat:latest",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            response = requests.post(url, headers=headers, json=data, verify=False)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return "Ошибка API GigaChat"
                
        except Exception as e:
            print(f"❌ Ошибка запроса к API: {e}")
            return "Ошибка соединения с GigaChat"
    
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
