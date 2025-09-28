# -*- coding: utf-8 -*-
"""
Sber GigaChat API SDK
Продвинутая обертка для AI МАГИСТРА
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass

# Offline fallback
try:
    from offline_llm import OfflineLLM
    OFFLINE_AVAILABLE = True
except ImportError:
    OFFLINE_AVAILABLE = False


@dataclass
class GigaChatConfig:
    """Конфигурация GigaChat API"""
    api_url: str = "https://gigachat.devices.sberbank.ru/api/v1"
    client_id: str = ""
    client_secret: str = ""
    scope: str = "GIGACHAT_API_PERS"
    timeout: int = 30
    max_retries: int = 3
    verify_ssl: bool = True
    ca_bundle: Optional[str] = None


@dataclass
class BrainPersona:
    """Профиль личности AI Мага"""
    name: str
    style: str  # "aggressive", "professional", "friendly","boss"
    salary_target: int
    negotiation_tactics: List[str]
    forbidden_phrases: List[str]
    preferred_responses: Dict[str, List[str]]


class GigaChatSDK:
    """
    Продвинутая обертка для Sber GigaChat API
    """
    
    def __init__(self, config: GigaChatConfig):
        self.config = config
        self.access_token = None
        self.token_expires_at = None
        self.session_id = None
        self.conversation_history = []
        
    def authenticate(self) -> bool:
        """
        Аутентификация в GigaChat API
        """
        try:
            # Подготовка заголовков для Sber GigaChat
            auth_key = f"{self.config.client_id}:{self.config.client_secret}"
            import base64
            auth_header = base64.b64encode(auth_key.encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Получение токена доступа
            auth_data = {
                "scope": self.config.scope
            }
            
            # SSL настройки
            ssl_kwargs = {}
            if not self.config.verify_ssl:
                ssl_kwargs['verify'] = False
            elif self.config.ca_bundle:
                ssl_kwargs['verify'] = self.config.ca_bundle
            
            response = requests.post(
                f"{self.config.api_url}/oauth",
                data=auth_data,
                headers=headers,
                timeout=self.config.timeout,
                **ssl_kwargs
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                self.token_expires_at = datetime.now() + timedelta(seconds=token_data.get("expires_in", 3600))
                
                # Создание сессии
                self.session_id = f"ai_magistr_{int(time.time())}"
                
                print("✅ GigaChat API аутентификация успешна")
                return True
            else:
                print(f"❌ Ошибка аутентификации: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка подключения к GigaChat: {e}")
            return False
    
    def _ensure_token_valid(self) -> bool:
        """
        Проверка и обновление токена при необходимости
        """
        if not self.access_token or (self.token_expires_at and datetime.now() >= self.token_expires_at):
            return self.authenticate()
        return True
    
    def generate_response(self, prompt: str, context: Dict = None, persona: BrainPersona = None) -> Tuple[str, Dict]:
        """
        Генерация ответа через GigaChat с контекстом и личностью
        """
        try:
            if not self._ensure_token_valid():
                return "Ошибка аутентификации", {}
            
            # Подготовка промпта с личностью
            full_prompt = self._build_contextual_prompt(prompt, context, persona)
            
            # Запрос к API
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "GigaChat:latest",
                "messages": [
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            # SSL настройки
            ssl_kwargs = {}
            if not self.config.verify_ssl:
                ssl_kwargs['verify'] = False
            elif self.config.ca_bundle:
                ssl_kwargs['verify'] = self.config.ca_bundle
            
            response = requests.post(
                f"{self.config.api_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.config.timeout,
                **ssl_kwargs
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result["choices"][0]["message"]["content"]
                
                # Сохранение в историю
                self.conversation_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "user_prompt": prompt,
                    "ai_response": ai_response,
                    "context": context,
                    "persona": persona.name if persona else "default"
                })
                
                # Анализ ответа
                analysis = self._analyze_response(ai_response, persona)
                
                return ai_response, analysis
            else:
                print(f"❌ Ошибка API: {response.status_code}")
                return "Ошибка генерации ответа", {}
                
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            return "Произошла ошибка", {}
    
    def _build_contextual_prompt(self, prompt: str, context: Dict, persona: BrainPersona) -> str:
        """
        Построение контекстного промпта с личностью
        """
        if not persona:
            persona = self._get_default_persona()
        
        # Базовый промпт с личностью
        base_prompt = f"""
        Ты {persona.name} - {persona.style} переговорщик на собеседованиях.
        
        ЦЕЛЬ: Получить максимальную зарплату (цель: ${persona.salary_target:,}).
        
        СТИЛЬ ОБЩЕНИЯ: {persona.style}
        - Агрессивный: создавай конкуренцию, дави на слабые места
        - Профессиональный: вежливо, но твердо
        - Дружелюбный: мягко, но настойчиво
        
        ТАКТИКИ:
        {chr(10).join(f"- {tactic}" for tactic in persona.negotiation_tactics)}
        
        ЗАПРЕЩЕНО ГОВОРИТЬ:
        {chr(10).join(f"- {phrase}" for phrase in persona.forbidden_phrases)}
        """
        
        # Добавление контекста
        if context:
            context_str = "\nКОНТЕКСТ:\n"
            if context.get("screen_text"):
                context_str += f"На экране: {context['screen_text'][:200]}...\n"
            if context.get("market_data"):
                context_str += f"Рыночные данные: {context['market_data']}\n"
            if context.get("conversation_history"):
                context_str += f"История: {context['conversation_history'][-3:]}\n"
            
            base_prompt += context_str
        
        # Добавление текущего сообщения
        base_prompt += f"\nСООБЩЕНИЕ HR: {prompt}\n\nОтветь как {persona.name}:"
        
        return base_prompt
    
    def _get_default_persona(self) -> BrainPersona:
        """
        Получение дефолтной личности
        """
        return BrainPersona(
            name="AI МАГИСТР",
            style="aggressive",
            salary_target=200000,
            negotiation_tactics=[
                "Создавай конкуренцию: 'У меня есть другие предложения'",
                "Дави на слабые места: 'Это ниже рыночной'",
                "Задавай встречные вопросы: 'А что у вас уникального?'",
                "Используй временное давление: 'У меня есть еще встречи'"
            ],
            forbidden_phrases=[
                "Мне все равно",
                "Любая зарплата подойдет",
                "Я готов на уступки",
                "У меня нет других вариантов"
            ],
            preferred_responses={
                "salary_low": [
                    "Интересно. А какая вилка у вас в голове?",
                    "Хм, это ниже рыночной. У меня есть предложения от 180k.",
                    "Давайте поговорим о компенсации. Что вы готовы предложить?"
                ],
                "technical": [
                    "Отличный вопрос! Расскажу на примере Prometheus...",
                    "В моем последнем проекте мы решили это через...",
                    "Да, это классическая задача. Вот как я бы подошел..."
                ]
            }
        )
    
    def _analyze_response(self, response: str, persona: BrainPersona) -> Dict:
        """
        Анализ сгенерированного ответа
        """
        analysis = {
            "length": len(response),
            "tone": "neutral",
            "negotiation_strength": "medium",
            "key_phrases": [],
            "salary_mentioned": False,
            "competition_created": False
        }
        
        # Анализ тона
        aggressive_words = ["давление", "конкуренция", "другие предложения", "рыночная"]
        if any(word in response.lower() for word in aggressive_words):
            analysis["tone"] = "aggressive"
            analysis["negotiation_strength"] = "high"
        
        # Поиск ключевых фраз
        for phrase in persona.negotiation_tactics:
            if any(word in response.lower() for word in phrase.lower().split()):
                analysis["key_phrases"].append(phrase)
        
        # Проверка упоминания зарплаты
        salary_words = ["зарплата", "salary", "компенсация", "деньги", "вилка"]
        analysis["salary_mentioned"] = any(word in response.lower() for word in salary_words)
        
        # Проверка создания конкуренции
        competition_words = ["другие предложения", "еще встречи", "рассматриваю"]
        analysis["competition_created"] = any(word in response.lower() for word in competition_words)
        
        return analysis
    
    def get_conversation_summary(self) -> Dict:
        """
        Получение сводки разговора
        """
        if not self.conversation_history:
            return {"message": "Разговор еще не начался"}
        
        total_interactions = len(self.conversation_history)
        salary_discussions = sum(1 for msg in self.conversation_history 
                               if "зарплата" in msg["user_prompt"].lower() or 
                                  "salary" in msg["user_prompt"].lower())
        
        return {
            "total_interactions": total_interactions,
            "salary_discussions": salary_discussions,
            "average_response_length": sum(len(msg["ai_response"]) for msg in self.conversation_history) / total_interactions,
            "last_interaction": self.conversation_history[-1]["timestamp"] if self.conversation_history else None
        }
    
    def clear_history(self):
        """
        Очистка истории разговора
        """
        self.conversation_history = []
        print("🧹 История разговора очищена")


class BrainManager:
    """
    Менеджер мозга AI МАГИСТРА
    """
    
    def __init__(self, config: GigaChatConfig):
        self.sdk = GigaChatSDK(config)

        # Offline fallback
        self.offline_llm = None
        if OFFLINE_AVAILABLE:
            self.offline_llm = OfflineLLM()

        self.personas = {}
        self.current_persona = None
        self.is_authenticated = False
        
    def initialize(self) -> bool:
        """
        Инициализация мозга
        """
        try:
            # Аутентификация
            self.is_authenticated = self.sdk.authenticate()
            
            if self.is_authenticated:
                # Загрузка личностей
                self._load_personas()
                self.current_persona = self.personas.get("aggressive", self.sdk._get_default_persona())
                
                print("🧠 Мозг AI МАГИСТРА инициализирован")
                return True
            else:
                print("❌ Ошибка инициализации мозга")
                return False
                
        except Exception as e:
            print(f"❌ Критическая ошибка мозга: {e}")
            return False
    
    def _load_personas(self):
        """
        Загрузка личностей
        """
        self.personas = {
            "aggressive": BrainPersona(
                name="Агрессивный МАГИСТР",
                style="aggressive",
                salary_target=200000,
                negotiation_tactics=[
                    "Создавай конкуренцию: 'У меня есть другие предложения'",
                    "Дави на слабые места: 'Это ниже рыночной'",
                    "Используй временное давление: 'У меня есть еще встречи'"
                ],
                forbidden_phrases=["Мне все равно", "Любая зарплата подойдет"],
                preferred_responses={}
            ),
            "professional": BrainPersona(
                name="Профессиональный МАГИСТР",
                style="professional",
                salary_target=180000,
                negotiation_tactics=[
                    "Вежливо, но твердо: 'Моя цель немного выше'",
                    "Задавай встречные вопросы: 'А что у вас уникального?'"
                ],
                forbidden_phrases=["Агрессивные фразы"],
                preferred_responses={}
            ),
            "friendly": BrainPersona(
                name="Дружелюбный МАГИСТР",
                style="friendly",
                salary_target=160000,
                negotiation_tactics=[
                    "Мягко, но настойчиво: 'Можем обсудить компенсацию?'",
                    "Создавай позитивную атмосферу"
                ],
                forbidden_phrases=["Агрессивные фразы", "Давление"],
                preferred_responses={}
            )
        }
    
    def switch_persona(self, persona_name: str) -> bool:
        """
        Переключение личности
        """
        if persona_name in self.personas:
            self.current_persona = self.personas[persona_name]
            print(f"🎭 Переключено на личность: {self.current_persona.name}")
            return True
        return False
    
    def process_hr_message(self, message: str, context: Dict = None) -> Tuple[str, Dict]:
        """
        Обработка сообщения HR с offline fallback
        """
        if context is None:
            context = {}

        # Пытаемся использовать GigaChat
        if self.is_authenticated:
            try:
                response, analysis = self.sdk.generate_response(message, context, self.current_persona)

                # Проверяем валидность ответа
                if response and len(response.strip()) > 10:  # Минимальная длина ответа
                    return response, analysis

                print("[BrainManager] GigaChat вернул пустой ответ, переключаюсь на offline")

            except Exception as e:
                print(f"[BrainManager] Ошибка GigaChat API: {e}")

        # Fallback на offline LLM
        if self.offline_llm and self.offline_llm.is_available:
            try:
                print("[BrainManager] Использую offline LLM fallback")

                # Адаптируем контекст для offline LLM
                offline_context = {
                    "task": context.get("task", "general"),
                    "company": context.get("company"),
                    "position": context.get("position")
                }

                response = self.offline_llm.generate_response(message, offline_context)

                analysis = {
                    "source": "offline_llm",
                    "intent": self.offline_llm._classify_intent(message, offline_context),
                    "fallback": True
                }

                return response, analysis

            except Exception as e:
                print(f"[BrainManager] Ошибка offline LLM: {e}")

        # Последний fallback - простые ответы
        print("[BrainManager] Использую базовый fallback")

        fallback_responses = {
            "salary": "Давайте обсудим компенсацию. Какая вилка у вас в голове?",
            "technical": "Отличный вопрос! Расскажу на примере своего опыта.",
            "company": "Интересная компания. Что вас в ней привлекает?",
            "default": "Понял. Расскажите подробнее о вашем опыте."
        }

        # Простая классификация
        message_lower = message.lower()
        if any(word in message_lower for word in ["зарплат", "компенсац", "salary"]):
            response = fallback_responses["salary"]
        elif any(word in message_lower for word in ["техническ", "код", "систем"]):
            response = fallback_responses["technical"]
        elif any(word in message_lower for word in ["компани", "фирм"]):
            response = fallback_responses["company"]
        else:
            response = fallback_responses["default"]

        analysis = {
            "source": "basic_fallback",
            "fallback": True
        }

        return response, analysis


# =============== ТЕСТИРОВАНИЕ ===============

def test_brain_sdk():
    """
    Тестирование SDK мозга
    """
    print("🧪 Тестирование Brain SDK...")
    
    # Конфигурация (заглушка)
    config = GigaChatConfig(
        client_id="test_id",
        client_secret="test_secret"
    )
    
    # Создание менеджера
    brain_manager = BrainManager(config)
    
    # Инициализация (заглушка)
    print("🔧 Инициализация мозга...")
    # brain_manager.initialize()  # Раскомментировать при наличии API ключей
    
    # Тест обработки сообщений
    test_messages = [
        "Какая у вас зарплата?",
        "Расскажите о вашем опыте с Python",
        "Мы предлагаем $120k"
    ]
    
    for message in test_messages:
        print(f"\n👤 HR: {message}")
        # response, analysis = brain_manager.process_hr_message(message)
        # print(f"🤖 AI МАГИСТР: {response}")
        # print(f"📊 Анализ: {analysis}")
        print("🤖 AI МАГИСТР: [Заглушка - нужен API ключ]")


if __name__ == "__main__":
    test_brain_sdk()
