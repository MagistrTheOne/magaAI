# -*- coding: utf-8 -*-
"""
Yandex Vision интеграция
"""

import os
import base64
import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
import time

try:
    from yandex_cloud_ml_sdk import YCloudML
    YANDEX_SDK_AVAILABLE = True
except ImportError:
    print("Warning: yandex-cloud-ml-sdk не установлен")
    YANDEX_SDK_AVAILABLE = False


class YandexVision:
    """
    Yandex Vision интеграция для анализа изображений
    """
    
    def __init__(self):
        self.logger = logging.getLogger("YandexVision")
        
        # Конфигурация
        self.api_key = os.getenv('YANDEX_API_KEY')
        self.folder_id = os.getenv('YANDEX_FOLDER_ID')
        self.enabled = os.getenv('YANDEX_VISION_ENABLED', 'true').lower() == 'true'
        
        # Клиент
        self.client = None
        self.is_authenticated = False
        
        # Кэш результатов
        self.analysis_cache = {}
        
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
                self.logger.info("Yandex Vision отключен")
                return
            
            # Инициализация клиента
            self.client = YCloudML(api_key=self.api_key)
            self.is_authenticated = True
            
            self.logger.info("Yandex Vision инициализирован")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации Yandex Vision: {e}")
            self.is_authenticated = False
    
    def _encode_image(self, image_path: str) -> str:
        """Кодирование изображения в base64"""
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                return encoded_string
        except Exception as e:
            self.logger.error(f"Ошибка кодирования изображения: {e}")
            return ""
    
    async def analyze_image(self, image_path: str, analysis_type: str = "general") -> Dict[str, Any]:
        """Анализ изображения"""
        try:
            if not self.enabled or not self.is_authenticated:
                return {"error": "Yandex Vision отключен или не аутентифицирован"}
            
            # Проверяем кэш
            cache_key = f"{image_path}_{analysis_type}"
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]
            
            # Кодируем изображение
            image_data = self._encode_image(image_path)
            if not image_data:
                return {"error": "Не удалось закодировать изображение"}
            
            # Параметры анализа
            vision_params = {
                "image": image_data,
                "folderId": self.folder_id
            }
            
            # Вызов API Vision
            response = self.client.vision.analyze(**vision_params)
            
            # Обработка результата
            result = {
                "analysis_type": analysis_type,
                "timestamp": time.time(),
                "image_path": image_path
            }
            
            if hasattr(response, 'text_detection'):
                result["text_detection"] = response.text_detection
            
            if hasattr(response, 'face_detection'):
                result["face_detection"] = response.face_detection
            
            if hasattr(response, 'object_detection'):
                result["object_detection"] = response.object_detection
            
            if hasattr(response, 'classification'):
                result["classification"] = response.classification
            
            # Сохраняем в кэш
            self.analysis_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа изображения: {e}")
            return {"error": str(e)}
    
    async def extract_text(self, image_path: str) -> str:
        """Извлечение текста из изображения (OCR)"""
        try:
            if not self.enabled or not self.is_authenticated:
                return ""
            
            # Кодируем изображение
            image_data = self._encode_image(image_path)
            if not image_data:
                return ""
            
            # Параметры OCR
            ocr_params = {
                "image": image_data,
                "folderId": self.folder_id
            }
            
            # Вызов API OCR
            response = self.client.vision.text_detection(**ocr_params)
            
            # Извлечение текста
            if hasattr(response, 'text_annotations') and response.text_annotations:
                # Объединяем все найденные тексты
                texts = []
                for annotation in response.text_annotations:
                    if hasattr(annotation, 'description'):
                        texts.append(annotation.description)
                
                return " ".join(texts)
            else:
                return ""
                
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста: {e}")
            return ""
    
    async def detect_objects(self, image_path: str) -> List[Dict[str, Any]]:
        """Детекция объектов на изображении"""
        try:
            if not self.enabled or not self.is_authenticated:
                return []
            
            # Кодируем изображение
            image_data = self._encode_image(image_path)
            if not image_data:
                return []
            
            # Параметры детекции объектов
            detection_params = {
                "image": image_data,
                "folderId": self.folder_id
            }
            
            # Вызов API детекции объектов
            response = self.client.vision.object_detection(**detection_params)
            
            # Обработка результатов
            objects = []
            if hasattr(response, 'localized_object_annotations'):
                for annotation in response.localized_object_annotations:
                    obj = {
                        "name": getattr(annotation, 'name', 'Unknown'),
                        "score": getattr(annotation, 'score', 0.0),
                        "bounding_box": getattr(annotation, 'bounding_box', {})
                    }
                    objects.append(obj)
            
            return objects
            
        except Exception as e:
            self.logger.error(f"Ошибка детекции объектов: {e}")
            return []
    
    async def detect_faces(self, image_path: str) -> List[Dict[str, Any]]:
        """Детекция лиц на изображении"""
        try:
            if not self.enabled or not self.is_authenticated:
                return []
            
            # Кодируем изображение
            image_data = self._encode_image(image_path)
            if not image_data:
                return []
            
            # Параметры детекции лиц
            face_params = {
                "image": image_data,
                "folderId": self.folder_id
            }
            
            # Вызов API детекции лиц
            response = self.client.vision.face_detection(**face_params)
            
            # Обработка результатов
            faces = []
            if hasattr(response, 'face_annotations'):
                for annotation in response.face_annotations:
                    face = {
                        "bounding_box": getattr(annotation, 'bounding_poly', {}),
                        "landmarks": getattr(annotation, 'landmarks', []),
                        "emotions": getattr(annotation, 'emotions', []),
                        "age": getattr(annotation, 'age', None),
                        "gender": getattr(annotation, 'gender', None)
                    }
                    faces.append(face)
            
            return faces
            
        except Exception as e:
            self.logger.error(f"Ошибка детекции лиц: {e}")
            return []
    
    async def classify_image(self, image_path: str) -> List[Dict[str, Any]]:
        """Классификация изображения"""
        try:
            if not self.enabled or not self.is_authenticated:
                return []
            
            # Кодируем изображение
            image_data = self._encode_image(image_path)
            if not image_data:
                return []
            
            # Параметры классификации
            classification_params = {
                "image": image_data,
                "folderId": self.folder_id
            }
            
            # Вызов API классификации
            response = self.client.vision.classify(**classification_params)
            
            # Обработка результатов
            classifications = []
            if hasattr(response, 'classifications'):
                for classification in response.classifications:
                    cls = {
                        "name": getattr(classification, 'name', 'Unknown'),
                        "score": getattr(classification, 'score', 0.0),
                        "category": getattr(classification, 'category', 'Unknown')
                    }
                    classifications.append(cls)
            
            return classifications
            
        except Exception as e:
            self.logger.error(f"Ошибка классификации изображения: {e}")
            return []
    
    def get_supported_formats(self) -> List[str]:
        """Получение поддерживаемых форматов изображений"""
        return ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"]
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Получение статистики использования"""
        return {
            "enabled": self.enabled,
            "authenticated": self.is_authenticated,
            "cache_size": len(self.analysis_cache),
            "supported_formats": len(self.get_supported_formats())
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья сервиса"""
        try:
            if not self.enabled:
                return {
                    "status": "disabled",
                    "message": "Yandex Vision отключен"
                }
            
            if not self.is_authenticated:
                return {
                    "status": "error",
                    "message": "Не аутентифицирован"
                }
            
            return {
                "status": "healthy",
                "message": "Yandex Vision работает",
                "supported_formats": self.get_supported_formats()
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)}"
            }


# Функция для тестирования
async def test_yandex_vision():
    """Тестирование Yandex Vision"""
    vision = YandexVision()
    
    print("👁️ Тестирование Yandex Vision...")
    print(f"Статус: {'✅ Включен' if vision.enabled else '❌ Отключен'}")
    print(f"Аутентификация: {'✅ Да' if vision.is_authenticated else '❌ Нет'}")
    
    if vision.enabled and vision.is_authenticated:
        # Статистика
        stats = vision.get_usage_stats()
        print(f"Статистика: {stats}")
        
        # Поддерживаемые форматы
        formats = vision.get_supported_formats()
        print(f"Поддерживаемые форматы: {', '.join(formats)}")


if __name__ == "__main__":
    asyncio.run(test_yandex_vision())
