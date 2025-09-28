# -*- coding: utf-8 -*-
"""
Yandex Translate интеграция
"""

import os
import asyncio
import logging
from typing import Dict, List, Optional, Any
import time

try:
    from yandex_cloud_ml_sdk import YCloudML
    YANDEX_SDK_AVAILABLE = True
except ImportError:
    print("Warning: yandex-cloud-ml-sdk не установлен")
    YANDEX_SDK_AVAILABLE = False


class YandexTranslate:
    """
    Yandex Translate интеграция
    """
    
    def __init__(self):
        self.logger = logging.getLogger("YandexTranslate")
        
        # Конфигурация
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.enabled = os.getenv('YANDEX_TRANSLATE_ENABLED', 'true').lower() == 'true'
        
        # Клиент
        self.client = None
        self.is_authenticated = False
        
        # Кэш переводов
        self.translation_cache = {}
        
        # Инициализация
        self._init_client()
    
    def _init_client(self):
        """Инициализация клиента"""
        try:
            if not YANDEX_SDK_AVAILABLE:
                self.logger.warning("Yandex SDK недоступен")
                return
            
            if not self.api_key:
                self.logger.warning("YANDEX_API_KEY не установлен")
                return
            
            if not self.enabled:
                self.logger.info("Yandex Translate отключен")
                return
            
            # Инициализация клиента
            self.client = YCloudML(api_key=self.api_key)
            self.is_authenticated = True
            
            self.logger.info("Yandex Translate инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Yandex Translate: {e}")
            self.is_authenticated = False
    
    async def translate(self, text: str, target_lang: str = "ru", source_lang: str = "auto") -> str:
        """Перевод текста"""
        try:
            if not self.enabled or not self.is_authenticated:
                return text
            
            # Проверяем кэш
            cache_key = f"{text}_{source_lang}_{target_lang}"
            if cache_key in self.translation_cache:
                return self.translation_cache[cache_key]
            
            # Параметры перевода
            translate_params = {
                "texts": [text],
                "targetLanguageCode": target_lang,
                "sourceLanguageCode": source_lang,
                "folderId": self.folder_id
            }
            
            # Вызов API перевода
            response = self.client.translate.translate(**translate_params)
            
            # Извлечение результата
            if response.translations and len(response.translations) > 0:
                translated_text = response.translations[0].text
                
                # Сохраняем в кэш
                self.translation_cache[cache_key] = translated_text
                
                return translated_text
            else:
                return text
                
        except Exception as e:
            self.logger.error(f"Ошибка перевода: {e}")
            return text
    
    async def translate_batch(self, texts: List[str], target_lang: str = "ru", source_lang: str = "auto") -> List[str]:
        """Пакетный перевод"""
        try:
            if not self.enabled or not self.is_authenticated:
                return texts
            
            # Параметры перевода
            translate_params = {
                "texts": texts,
                "targetLanguageCode": target_lang,
                "sourceLanguageCode": source_lang,
                "folderId": self.folder_id
            }
            
            # Вызов API перевода
            response = self.client.translate.translate(**translate_params)
            
            # Извлечение результатов
            if response.translations:
                return [translation.text for translation in response.translations]
            else:
                return texts
                
        except Exception as e:
            self.logger.error(f"Ошибка пакетного перевода: {e}")
            return texts
    
    async def detect_language(self, text: str) -> str:
        """Определение языка текста"""
        try:
            if not self.enabled or not self.is_authenticated:
                return "auto"
            
            # Параметры определения языка
            detect_params = {
                "text": text,
                "folderId": self.folder_id
            }
            
            # Вызов API определения языка
            response = self.client.translate.detect_language(**detect_params)
            
            # Извлечение результата
            if response.languageCode:
                return response.languageCode
            else:
                return "auto"
                
        except Exception as e:
            self.logger.error(f"Ошибка определения языка: {e}")
            return "auto"
    
    def get_supported_languages(self) -> List[str]:
        """Получение поддерживаемых языков"""
        return [
            "ru", "en", "es", "fr", "de", "it", "pt", "zh", "ja", "ko",
            "ar", "hi", "tr", "pl", "nl", "sv", "da", "no", "fi", "cs",
            "hu", "ro", "bg", "hr", "sk", "sl", "et", "lv", "lt", "uk"
        ]
    
    def get_language_name(self, lang_code: str) -> str:
        """Получение названия языка"""
        lang_names = {
            "ru": "Русский",
            "en": "Английский",
            "es": "Испанский",
            "fr": "Французский",
            "de": "Немецкий",
            "it": "Итальянский",
            "pt": "Португальский",
            "zh": "Китайский",
            "ja": "Японский",
            "ko": "Корейский",
            "ar": "Арабский",
            "hi": "Хинди",
            "tr": "Турецкий",
            "pl": "Польский",
            "nl": "Голландский",
            "sv": "Шведский",
            "da": "Датский",
            "no": "Норвежский",
            "fi": "Финский",
            "cs": "Чешский",
            "hu": "Венгерский",
            "ro": "Румынский",
            "bg": "Болгарский",
            "hr": "Хорватский",
            "sk": "Словацкий",
            "sl": "Словенский",
            "et": "Эстонский",
            "lv": "Латышский",
            "lt": "Литовский",
            "uk": "Украинский"
        }
        return lang_names.get(lang_code, lang_code)
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Получение статистики использования"""
        return {
            "enabled": self.enabled,
            "authenticated": self.is_authenticated,
            "cache_size": len(self.translation_cache),
            "supported_languages": len(self.get_supported_languages())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья сервиса"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "Yandex Translate отключен"
                }
            
            if not self.is_authenticated:
                return {
                    "status": "error",
                    "message": "Не аутентифицирован"
                }
            
            # Простой тест
            test_text = "Hello world"
            translated = await self.translate(test_text, "ru")
            
            return {
                "status": "healthy",
                "message": "Yandex Translate работает",
                "test_translation": f"{test_text} -> {translated}"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)}"
            }


# Функция для тестирования
async def test_yandex_translate():
    """Тестирование Yandex Translate"""
    translator = YandexTranslate()
    
    print("🌐 Тестирование Yandex Translate...")
    print(f"Статус: {'✅ Включен' if translator.enabled else '❌ Отключен'}")
    print(f"Аутентификация: {'✅ Да' if translator.is_authenticated else '❌ Нет'}")
    
    if translator.enabled and translator.is_authenticated:
        # Тест перевода
        test_text = "Hello, how are you?"
        translated = await translator.translate(test_text, "ru")
        print(f"Перевод: {test_text} -> {translated}")
        
        # Тест определения языка
        detected = await translator.detect_language("Привет, как дела?")
        print(f"Определенный язык: {detected}")
        
        # Статистика
        stats = translator.get_usage_stats()
        print(f"Статистика: {stats}")


if __name__ == "__main__":
    asyncio.run(test_yandex_translate())
