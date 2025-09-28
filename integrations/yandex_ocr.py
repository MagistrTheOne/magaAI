# -*- coding: utf-8 -*-
"""
Yandex OCR интеграция для AIMagistr 3.0
"""

import os
import base64
import asyncio
import logging
import requests
from typing import Dict, List, Optional, Any
import time


class YandexOCR:
    """
    Yandex OCR интеграция для распознавания текста
    """
    
    def __init__(self):
        self.logger = logging.getLogger("YandexOCR")
        
        # Конфигурация
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.enabled = os.getenv('YANDEX_OCR_ENABLED', 'true').lower() == 'true'
        self.api_url = os.getenv('YANDEX_OCR_API_URL', 'https://ocr.api.cloud.yandex.net/ocr/v1/recognizeText')
        
        # HTTP клиент
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Api-Key {self.api_key}',
            'Content-Type': 'application/json'
        })
        
        # Кэш результатов
        self.ocr_cache = {}
        
        # Инициализация
        self._init_client()
    
    def _init_client(self):
        """Инициализация клиента"""
        try:
            if not self.api_key:
                self.logger.warning("YANDEX_API_KEY не установлен")
                return
            
            if not self.enabled:
                self.logger.info("Yandex OCR отключен")
                return
            
            self.logger.info("Yandex OCR инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Yandex OCR: {e}")
    
    def _encode_image(self, image_path: str) -> str:
        """Кодирование изображения в base64"""
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            self.logger.error(f"Ошибка кодирования изображения: {e}")
            return ""
    
    async def recognize_text(self, image_path: str, language_codes: List[str] = None) -> Dict[str, Any]:
        """Распознавание текста на изображении"""
        try:
            if not self.enabled:
                return {"error": "Yandex OCR отключен"}
            
            # Проверяем кэш
            cache_key = f"{image_path}_{language_codes}"
            if cache_key in self.ocr_cache:
                return self.ocr_cache[cache_key]
            
            # Кодируем изображение
            image_data = self._encode_image(image_path)
            if not image_data:
                return {"error": "Не удалось закодировать изображение"}
            
            # Параметры OCR
            if language_codes is None:
                language_codes = ["ru", "en"]
            
            payload = {
                "mime_type": "image/jpeg",
                "language_codes": language_codes,
                "model": "page",
                "content": image_data
            }
            
            # Вызов API OCR
            response = self.session.post(
                self.api_url,
                json=payload,
                params={'folderId': self.folder_id}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Обработка результата
                ocr_result = {
                    "success": True,
                    "timestamp": time.time(),
                    "image_path": image_path,
                    "language_codes": language_codes,
                    "text_blocks": [],
                    "full_text": "",
                    "confidence": 0.0
                }
                
                # Извлечение текста
                text_blocks = []
                total_confidence = 0.0
                block_count = 0
                
                for page in result.get('result', {}).get('pages', []):
                    for block in page.get('blocks', []):
                        block_text = ""
                        block_confidence = 0.0
                        
                        for line in block.get('lines', []):
                            line_text = ""
                            line_confidence = 0.0
                            
                            for word in line.get('words', []):
                                word_text = word.get('text', '')
                                word_confidence = word.get('confidence', 0.0)
                                
                                if word_text:
                                    line_text += word_text + " "
                                    line_confidence += word_confidence
                            
                            if line_text.strip():
                                block_text += line_text.strip() + "\n"
                                block_confidence += line_confidence
                        
                        if block_text.strip():
                            text_blocks.append({
                                "text": block_text.strip(),
                                "confidence": block_confidence / max(1, len(block.get('lines', []))),
                                "bounding_box": block.get('boundingBox', {})
                            })
                            total_confidence += block_confidence
                            block_count += 1
                
                # Объединяем весь текст
                full_text = "\n".join([block["text"] for block in text_blocks])
                
                ocr_result.update({
                    "text_blocks": text_blocks,
                    "full_text": full_text,
                    "confidence": total_confidence / max(1, block_count)
                })
                
                # Сохраняем в кэш
                self.ocr_cache[cache_key] = ocr_result
                
                return ocr_result
                
            else:
                return {
                    "error": f"Ошибка OCR API: {response.status_code}",
                    "response": response.text
                }
                
        except Exception as e:
            self.logger.error(f"Ошибка распознавания текста: {e}")
            return {"error": str(e)}
    
    async def extract_text_simple(self, image_path: str) -> str:
        """Простое извлечение текста (только текст)"""
        try:
            result = await self.recognize_text(image_path)
            
            if result.get("success"):
                return result.get("full_text", "")
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Ошибка простого извлечения текста: {e}")
            return ""
    
    async def recognize_text_with_confidence(self, image_path: str, min_confidence: float = 0.5) -> Dict[str, Any]:
        """Распознавание текста с фильтрацией по уверенности"""
        try:
            result = await self.recognize_text(image_path)
            
            if not result.get("success"):
                return result
            
            # Фильтруем блоки по уверенности
            filtered_blocks = [
                block for block in result.get("text_blocks", [])
                if block.get("confidence", 0.0) >= min_confidence
            ]
            
            # Обновляем результат
            result["text_blocks"] = filtered_blocks
            result["full_text"] = "\n".join([block["text"] for block in filtered_blocks])
            result["filtered_confidence"] = min_confidence
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка распознавания с фильтрацией: {e}")
            return {"error": str(e)}
    
    def get_supported_languages(self) -> List[str]:
        """Получение поддерживаемых языков"""
        return [
            "ru", "en", "uk", "kk", "uz", "az", "ky", "tt", "ba", "cv",
            "es", "fr", "de", "it", "pt", "pl", "tr", "ar", "zh", "ja", "ko"
        ]
    
    def get_language_name(self, lang_code: str) -> str:
        """Получение названия языка"""
        lang_names = {
            "ru": "Русский",
            "en": "Английский",
            "uk": "Украинский",
            "kk": "Казахский",
            "uz": "Узбекский",
            "az": "Азербайджанский",
            "ky": "Киргизский",
            "tt": "Татарский",
            "ba": "Башкирский",
            "cv": "Чувашский",
            "es": "Испанский",
            "fr": "Французский",
            "de": "Немецкий",
            "it": "Итальянский",
            "pt": "Португальский",
            "pl": "Польский",
            "tr": "Турецкий",
            "ar": "Арабский",
            "zh": "Китайский",
            "ja": "Японский",
            "ko": "Корейский"
        }
        return lang_names.get(lang_code, lang_code)
    
    def get_supported_formats(self) -> List[str]:
        """Получение поддерживаемых форматов изображений"""
        return ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"]
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Получение статистики использования"""
        return {
            "enabled": self.enabled,
            "cache_size": len(self.ocr_cache),
            "supported_languages": len(self.get_supported_languages()),
            "supported_formats": len(self.get_supported_formats())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья сервиса"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "Yandex OCR отключен"
                }
            
            if not self.api_key:
                return {
                    "status": "error",
                    "message": "API ключ не установлен"
                }
            
            return {
                "status": "healthy",
                "message": "Yandex OCR работает",
                "supported_languages": self.get_supported_languages(),
                "supported_formats": self.get_supported_formats()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)}"
            }
    
    def clear_cache(self):
        """Очистка кэша"""
        self.ocr_cache.clear()
        self.logger.info("Кэш OCR очищен")


# Функция для тестирования
async def test_yandex_ocr():
    """Тестирование Yandex OCR"""
    ocr = YandexOCR()
    
    print("Testing Yandex OCR...")
    print(f"Status: {'Enabled' if ocr.enabled else 'Disabled'}")
    
    if ocr.enabled:
        # Статистика
        stats = ocr.get_usage_stats()
        print(f"Stats: {stats}")
        
        # Поддерживаемые языки
        languages = ocr.get_supported_languages()
        print(f"Languages: {', '.join(languages[:10])}...")
        
        # Поддерживаемые форматы
        formats = ocr.get_supported_formats()
        print(f"Formats: {', '.join(formats)}")
        
        # Health check
        health = await ocr.health_check()
        print(f"Health: {health}")


if __name__ == "__main__":
    asyncio.run(test_yandex_ocr())
