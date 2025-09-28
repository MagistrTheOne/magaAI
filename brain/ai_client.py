# -*- coding: utf-8 -*-
"""
Единый AI клиент для Yandex AI Studio
Заменяет GigaChat SDK с совместимым интерфейсом
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
from dataclasses import dataclass
import time

try:
    from yandex_cloud_ml_sdk import YCloudML
    from yandex_cloud_ml_sdk.exceptions import YCloudMLException
    YANDEX_SDK_AVAILABLE = True
except ImportError:
    print("Warning: yandex-cloud-ml-sdk не установлен")
    YANDEX_SDK_AVAILABLE = False


@dataclass
class AIResponse:
    """Стандартизированный ответ AI"""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str
    timestamp: float


@dataclass
class AIStreamChunk:
    """Чанк стримингового ответа"""
    content: str
    delta: str
    finish_reason: Optional[str] = None


class BrainManager:
    """
    Единый AI клиент для Yandex AI Studio
    Совместимый интерфейс с предыдущим GigaChat SDK
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BrainManager")
        
        # Конфигурация
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.model_uri = os.getenv('YANDEX_MODEL_URI', 'gpt://b1gej5c8msk7iqfjv11p/yandexgpt/latest')
        self.folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.system_prompt = os.getenv('SYSTEM_PROMPT', 'Ты Ассистент Мага - умный ИИ-помощник для автоматизации рутины и повышения продуктивности.')
        self.translate_enabled = os.getenv('YANDEX_TRANSLATE_ENABLED', 'false').lower() == 'true'
        self.vision_enabled = os.getenv('YANDEX_VISION_ENABLED', 'false').lower() == 'true'
        
        # Метрики
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_time': 0.0
        }
        
        # Клиент
        self.client = None
        self.is_authenticated = False
        
        # Настройки
        self.config = {
            'max_tokens': int(os.getenv('MAX_CONTEXT_TOKENS', '4000')),
            'temperature': 0.3,
            'top_p': 0.9,
            'stream': os.getenv('ENABLE_STREAMING', 'false').lower() == 'true',
            'timeout': int(os.getenv('REQUEST_TIMEOUT', '30')),
            'max_retries': int(os.getenv('MAX_RETRIES', '3'))
        }
        
        # Инициализация
        self._init_client()
    
    def _init_client(self):
        """Инициализация Yandex AI клиента"""
        try:
            if not YANDEX_SDK_AVAILABLE:
                self.logger.error("Yandex SDK недоступен")
                return
            
            if not self.api_key:
                self.logger.error("YANDEX_API_KEY не установлен")
                return
            
            # Инициализация клиента
            self.client = YCloudML(api_key=self.api_key)
            self.is_authenticated = True
            
            self.logger.info("Yandex AI клиент инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Yandex AI: {e}")
            self.is_authenticated = False
    
    async def generate_response(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Генерация ответа с системным промптом и ретраями"""
        start_time = time.time()
        self.metrics['total_requests'] += 1
        
        # Используем системный промпт по умолчанию
        if not system_prompt:
            system_prompt = self.system_prompt
        
        for attempt in range(self.config['max_retries']):
            try:
                if not self.is_authenticated:
                    self.metrics['failed_requests'] += 1
                    return "AI клиент не инициализирован"
                
                # Подготовка сообщений
                messages = [
                    {
                        "role": "system",
                        "text": system_prompt
                    },
                    {
                        "role": "user", 
                        "text": prompt
                    }
                ]
                
                # Параметры генерации
                generation_options = {
                    "max_tokens": kwargs.get('max_tokens', self.config['max_tokens']),
                    "temperature": kwargs.get('temperature', self.config['temperature']),
                    "top_p": kwargs.get('top_p', self.config['top_p'])
                }
                
                # Вызов API с таймаутом
                response = self.client.chat.completions.create(
                    model=self.model_uri,
                    messages=messages,
                    generation_options=generation_options
                )
                
                # Извлечение ответа
                if response.choices and len(response.choices) > 0:
                    content = response.choices[0].message.content
                    
                    # Обновляем метрики
                    self.metrics['successful_requests'] += 1
                    self.metrics['total_time'] += time.time() - start_time
                    
                    if hasattr(response, 'usage') and response.usage:
                        self.metrics['total_tokens'] += getattr(response.usage, 'total_tokens', 0)
                    
                    return content.strip()
                else:
                    if attempt < self.config['max_retries'] - 1:
                        await asyncio.sleep(1)  # Пауза перед повтором
                        continue
                    else:
                        self.metrics['failed_requests'] += 1
                        return "Пустой ответ от AI"
                        
            except Exception as e:
                self.logger.error(f"Ошибка генерации ответа (попытка {attempt + 1}): {e}")
                if attempt < self.config['max_retries'] - 1:
                    await asyncio.sleep(2 ** attempt)  # Экспоненциальная задержка
                    continue
                else:
                    self.metrics['failed_requests'] += 1
                    return f"Ошибка после {self.config['max_retries']} попыток: {str(e)}"
        
        self.metrics['failed_requests'] += 1
        return "Превышено максимальное количество попыток"
    
    async def generate_stream(self, prompt: str, system_prompt: str = None, **kwargs) -> AsyncGenerator[str, None]:
        """Стриминговая генерация ответа"""
        try:
            if not self.is_authenticated:
                yield "AI клиент не инициализирован"
                return
            
            # Подготовка сообщений
            messages = []
            
            if system_prompt:
                messages.append({
                    "role": "system",
                    "text": system_prompt
                })
            
            messages.append({
                "role": "user",
                "text": prompt
            })
            
            # Параметры генерации
            generation_options = {
                "max_tokens": kwargs.get('max_tokens', self.config['max_tokens']),
                "temperature": kwargs.get('temperature', self.config['temperature']),
                "top_p": kwargs.get('top_p', self.config['top_p']),
                "stream": True
            }
            
            # Стриминговый вызов
            stream = self.client.chat.completions.create(
                model=self.model_uri,
                messages=messages,
                generation_options=generation_options,
                stream=True
            )
            
            # Обработка чанков
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        yield delta.content
                        
        except Exception as e:
            self.logger.error(f"Ошибка стриминговой генерации: {e}")
            yield f"Ошибка: {str(e)}"
    
    async def analyze_text(self, text: str, analysis_type: str = "general") -> Dict[str, Any]:
        """Анализ текста"""
        try:
            if not self.is_authenticated:
                return {"error": "AI клиент не инициализирован"}
            
            # Промпт для анализа
            analysis_prompts = {
                "sentiment": "Проанализируй тональность текста: {text}",
                "keywords": "Извлеки ключевые слова из текста: {text}",
                "summary": "Создай краткое изложение: {text}",
                "general": "Проанализируй текст: {text}"
            }
            
            prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"]).format(text=text)
            
            response = await self.generate_response(prompt)
            
            return {
                "analysis_type": analysis_type,
                "result": response,
                "timestamp": time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа текста: {e}")
            return {"error": str(e)}
    
    async def translate_text(self, text: str, target_lang: str = "ru", source_lang: str = "auto") -> str:
        """Перевод текста"""
        try:
            if not self.translate_enabled:
                return text  # Возвращаем оригинал если перевод отключен
            
            if not self.is_authenticated:
                return text
            
            # Промпт для перевода
            lang_map = {
                "ru": "русский",
                "en": "английский", 
                "es": "испанский",
                "fr": "французский",
                "de": "немецкий"
            }
            
            target_lang_name = lang_map.get(target_lang, target_lang)
            
            prompt = f"Переведи следующий текст на {target_lang_name}: {text}"
            
            response = await self.generate_response(prompt)
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Ошибка перевода: {e}")
            return text
    
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Генерация эмбеддингов"""
        try:
            if not self.is_authenticated:
                return []
            
            # Простая заглушка - в реальности нужен отдельный API для эмбеддингов
            # Yandex пока не предоставляет embeddings API в AI Studio
            embeddings = []
            
            for text in texts:
                # Используем хеш как простую заглушку
                import hashlib
                hash_obj = hashlib.md5(text.encode())
                hash_bytes = hash_obj.digest()
                embedding = [float(b) for b in hash_bytes[:16]]  # 16-мерный вектор
                embeddings.append(embedding)
            
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации эмбеддингов: {e}")
            return []
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Получение статистики использования"""
        return {
            "provider": "yandex",
            "model": self.model_uri,
            "authenticated": self.is_authenticated,
            "translate_enabled": self.translate_enabled,
            "vision_enabled": self.vision_enabled,
            "config": self.config,
            "metrics": self.metrics
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Получение метрик производительности"""
        success_rate = 0
        if self.metrics['total_requests'] > 0:
            success_rate = self.metrics['successful_requests'] / self.metrics['total_requests']
        
        avg_time = 0
        if self.metrics['successful_requests'] > 0:
            avg_time = self.metrics['total_time'] / self.metrics['successful_requests']
        
        return {
            "total_requests": self.metrics['total_requests'],
            "successful_requests": self.metrics['successful_requests'],
            "failed_requests": self.metrics['failed_requests'],
            "success_rate": round(success_rate, 3),
            "total_tokens": self.metrics['total_tokens'],
            "avg_response_time": round(avg_time, 3),
            "total_time": round(self.metrics['total_time'], 3)
        }
    
    def reset_metrics(self):
        """Сброс метрик"""
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_time': 0.0
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья сервиса"""
        try:
            if not self.is_authenticated:
                return {
                    "status": "error",
                    "message": "Не аутентифицирован"
                }
            
            # Простой тест
            test_response = await self.generate_response("Привет", max_tokens=10)
            
            return {
                "status": "healthy",
                "message": "Yandex AI работает",
                "test_response": test_response[:50] + "..." if len(test_response) > 50 else test_response
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)}"
            }


# Функция для тестирования
async def test_ai_client():
    """Тестирование AI клиента"""
    brain = BrainManager()
    
    print("🧠 Тестирование Yandex AI клиента...")
    print(f"Статус: {'✅ Аутентифицирован' if brain.is_authenticated else '❌ Не аутентифицирован'}")
    
    if brain.is_authenticated:
        # Тест генерации
        response = await brain.generate_response("Расскажи коротко о Python")
        print(f"Ответ: {response}")
        
        # Тест перевода
        if brain.translate_enabled:
            translated = await brain.translate_text("Hello world", "ru")
            print(f"Перевод: {translated}")
        
        # Статистика
        stats = brain.get_usage_stats()
        print(f"Статистика: {stats}")


if __name__ == "__main__":
    asyncio.run(test_ai_client())
