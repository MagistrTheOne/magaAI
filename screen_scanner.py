# -*- coding: utf-8 -*-
"""
Screen Scanner Module
OCR активного окна с триггерами для автоматических действий
"""

import time
import threading
from typing import Optional, List, Callable, Dict
import cv2
import numpy as np
import pytesseract
import pygetwindow as gw
from PIL import Image
import psutil


class ScreenScanner:
    """
    Сканер экрана с OCR и триггерами
    """
    
    def __init__(self, 
                 trigger_words: List[str] = None,
                 on_trigger: Optional[Callable] = None,
                 scan_interval: float = 2.0,
                 confidence_threshold: float = 0.7):
        """
        Args:
            trigger_words: Слова-триггеры для поиска
            on_trigger: Callback при срабатывании триггера
            scan_interval: Интервал сканирования в секундах
            confidence_threshold: Порог уверенности OCR
        """
        self.trigger_words = trigger_words or [
            "оффер", "зарплата", "тестовое", "salary", "offer", 
            "компенсация", "бонус", "equity", "stock", "опцион"
        ]
        self.on_trigger = on_trigger
        self.scan_interval = scan_interval
        self.confidence_threshold = confidence_threshold
        
        # Состояние
        self.is_scanning = False
        self.scan_thread = None
        self.last_scan_time = 0
        self.last_text = ""
        self.trigger_history = []
        
        # Настройки OCR
        self.ocr_config = '--oem 3 --psm 6 -l rus+eng'
        
    def start_scanning(self):
        """Запуск сканирования экрана"""
        if self.is_scanning:
            return
            
        self.is_scanning = True
        self.scan_thread = threading.Thread(target=self._scan_worker, daemon=True)
        self.scan_thread.start()
        
    def stop_scanning(self):
        """Остановка сканирования экрана"""
        self.is_scanning = False
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=1.0)
            
    def set_trigger_words(self, words: List[str]):
        """Установить слова-триггеры"""
        self.trigger_words = words
        
    def set_trigger_callback(self, callback: Callable):
        """Установить callback для триггеров"""
        self.on_trigger = callback
        
    def _scan_worker(self):
        """Поток сканирования экрана"""
        while self.is_scanning:
            try:
                # Получаем активное окно
                active_window = self._get_active_window()
                if not active_window:
                    time.sleep(self.scan_interval)
                    continue
                    
                # Делаем скриншот
                screenshot = self._capture_window(active_window)
                if screenshot is None:
                    time.sleep(self.scan_interval)
                    continue
                    
                # OCR
                text = self._extract_text(screenshot)
                if not text:
                    time.sleep(self.scan_interval)
                    continue
                    
                # Проверяем триггеры
                triggers = self._check_triggers(text)
                if triggers:
                    self._handle_triggers(triggers, text, active_window)
                    
                self.last_text = text
                self.last_scan_time = time.time()
                
            except Exception as e:
                print(f"[ScreenScanner] Ошибка сканирования: {e}")
                
            time.sleep(self.scan_interval)
            
    def _get_active_window(self) -> Optional[gw.Window]:
        """Получить активное окно"""
        try:
            windows = gw.getAllWindows()
            for window in windows:
                if window.isActive and window.visible:
                    return window
            return None
        except Exception as e:
            print(f"[ScreenScanner] Ошибка получения окна: {e}")
            return None
            
    def _capture_window(self, window: gw.Window) -> Optional[np.ndarray]:
        """Сделать скриншот окна"""
        try:
            # Получаем координаты окна
            left, top, width, height = window.left, window.top, window.width, window.height
            
            # Делаем скриншот
            screenshot = Image.new('RGB', (width, height))
            screenshot.paste(Image.grab(bbox=(left, top, left + width, top + height)))
            
            # Конвертируем в OpenCV формат
            screenshot_cv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            return screenshot_cv
            
        except Exception as e:
            print(f"[ScreenScanner] Ошибка скриншота: {e}")
            return None
            
    def _extract_text(self, image: np.ndarray) -> str:
        """Извлечь текст из изображения"""
        try:
            # Предобработка изображения
            processed = self._preprocess_image(image)
            
            # OCR
            text = pytesseract.image_to_string(
                processed, 
                config=self.ocr_config
            )
            
            return text.strip()
            
        except Exception as e:
            print(f"[ScreenScanner] Ошибка OCR: {e}")
            return ""
            
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Предобработка изображения для OCR"""
        try:
            # Конвертируем в серый
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Убираем шум
            denoised = cv2.medianBlur(gray, 3)
            
            # Увеличиваем контраст
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)
            
            # Бинаризация
            _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            return binary
            
        except Exception as e:
            print(f"[ScreenScanner] Ошибка предобработки: {e}")
            return image
            
    def _check_triggers(self, text: str) -> List[str]:
        """Проверить триггеры в тексте"""
        triggers = []
        text_lower = text.lower()
        
        for word in self.trigger_words:
            if word.lower() in text_lower:
                triggers.append(word)
                
        return triggers
        
    def _handle_triggers(self, triggers: List[str], text: str, window: gw.Window):
        """Обработка сработавших триггеров"""
        try:
            # Логируем триггер
            trigger_info = {
                'triggers': triggers,
                'text': text[:200] + "..." if len(text) > 200 else text,
                'window': window.title,
                'timestamp': time.time()
            }
            self.trigger_history.append(trigger_info)
            
            # Ограничиваем историю
            if len(self.trigger_history) > 100:
                self.trigger_history = self.trigger_history[-50:]
                
            # Вызываем callback
            if self.on_trigger:
                self.on_trigger(triggers, text, window)
                
        except Exception as e:
            print(f"[ScreenScanner] Ошибка обработки триггеров: {e}")
            
    def get_trigger_history(self) -> List[Dict]:
        """Получить историю триггеров"""
        return self.trigger_history.copy()
        
    def clear_trigger_history(self):
        """Очистить историю триггеров"""
        self.trigger_history.clear()
        
    def get_last_text(self) -> str:
        """Получить последний распознанный текст"""
        return self.last_text
        
    def is_window_zoom(self, window: gw.Window) -> bool:
        """Проверить, является ли окно Zoom"""
        title_lower = window.title.lower()
        return any(keyword in title_lower for keyword in [
            'zoom', 'zoom meeting', 'zoom.us', 'zoom video'
        ])
        
    def is_window_teams(self, window: gw.Window) -> bool:
        """Проверить, является ли окно Teams"""
        title_lower = window.title.lower()
        return any(keyword in title_lower for keyword in [
            'microsoft teams', 'teams', 'teams meeting'
        ])
        
    def is_window_meet(self, window: gw.Window) -> bool:
        """Проверить, является ли окно Google Meet"""
        title_lower = window.title.lower()
        return any(keyword in title_lower for keyword in [
            'google meet', 'meet.google.com', 'meet'
        ])
        
    def get_meeting_type(self, window: gw.Window) -> str:
        """Определить тип встречи"""
        if self.is_window_zoom(window):
            return "zoom"
        elif self.is_window_teams(window):
            return "teams"
        elif self.is_window_meet(window):
            return "meet"
        else:
            return "unknown"
