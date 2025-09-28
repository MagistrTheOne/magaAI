# -*- coding: utf-8 -*-
"""
Компьютерное зрение для анализа экрана собеседования
AI МАГИСТР - Модуль зрения
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import pyautogui
from typing import Dict, List, Optional, Tuple


class ScreenAnalyzer:
    """
    Анализатор экрана для собеседований
    """
    
    def __init__(self):
        self.ocr_engine = "tesseract"
        self.face_detection = True
        self.slide_analysis = True
        self.face_cascade = None
        
        # Инициализация детекторов
        self._init_detectors()
        
    def _init_detectors(self):
        """
        Инициализация детекторов
        """
        try:
            # Детектор лиц
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            print("✅ Детектор лиц инициализирован")
        except Exception as e:
            print(f"⚠️ Ошибка инициализации детекторов: {e}")
    
    def capture_screen(self, region: Tuple[int, int, int, int] = None) -> np.ndarray:
        """
        Захват экрана
        """
        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Конвертация в OpenCV формат
            screen_array = np.array(screenshot)
            screen_array = cv2.cvtColor(screen_array, cv2.COLOR_RGB2BGR)
            
            return screen_array
        except Exception as e:
            print(f"❌ Ошибка захвата экрана: {e}")
            return None
    
    def extract_text_from_screen(self, screen_image: np.ndarray) -> str:
        """
        Извлечение текста с экрана (OCR)
        """
        try:
            # Конвертация в PIL Image
            pil_image = Image.fromarray(cv2.cvtColor(screen_image, cv2.COLOR_BGR2RGB))
            
            # OCR с Tesseract
            text = pytesseract.image_to_string(pil_image, lang='rus+eng')
            
            return text.strip()
        except Exception as e:
            print(f"❌ Ошибка OCR: {e}")
            return ""
    
    def detect_faces(self, screen_image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Детекция лиц на экране
        """
        try:
            if self.face_cascade is None:
                return []
            
            gray = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)
            
            return [(x, y, w, h) for (x, y, w, h) in faces]
        except Exception as e:
            print(f"❌ Ошибка детекции лиц: {e}")
            return []
    
    def analyze_meeting_screen(self, screen_image: np.ndarray) -> Dict:
        """
        Полный анализ экрана встречи
        """
        analysis = {
            "text_content": "",
            "faces_detected": 0,
            "is_presentation": False,
            "is_document": False,
            "emotions": [],
            "job_keywords": []
        }
        
        try:
            # Извлечение текста
            analysis["text_content"] = self.extract_text_from_screen(screen_image)
            
            # Детекция лиц
            faces = self.detect_faces(screen_image)
            analysis["faces_detected"] = len(faces)
            
            # Анализ типа контента
            analysis.update(self._analyze_content_type(screen_image))
            
            # Поиск ключевых слов о работе
            analysis["job_keywords"] = self._extract_job_keywords(analysis["text_content"])
            
        except Exception as e:
            print(f"❌ Ошибка анализа экрана: {e}")
        
        return analysis
    
    def _analyze_content_type(self, screen_image: np.ndarray) -> Dict:
        """
        Анализ типа контента (презентация, документ, etc.)
        """
        analysis = {
            "is_presentation": False,
            "is_document": False
        }
        
        try:
            # Поиск слайдов/презентаций
            # (упрощенная логика - в реальности нужен более сложный анализ)
            gray = cv2.cvtColor(screen_image, cv2.COLOR_BGR2GRAY)
            
            # Детекция прямоугольников (слайды)
            edges = cv2.Canny(gray, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Если много прямоугольников - возможно презентация
            if len(contours) > 10:
                analysis["is_presentation"] = True
            
            # Анализ плотности текста
            text_density = len(self.extract_text_from_screen(screen_image))
            if text_density > 500:  # Много текста
                analysis["is_document"] = True
                
        except Exception as e:
            print(f"❌ Ошибка анализа типа контента: {e}")
        
        return analysis
    
    def _extract_job_keywords(self, text: str) -> List[str]:
        """
        Извлечение ключевых слов о работе
        """
        job_keywords = [
            "зарплата", "salary", "компенсация", "деньги",
            "python", "java", "javascript", "ml", "ai",
            "удаленка", "remote", "офис", "команда",
            "проект", "задача", "ответственность",
            "опыт", "стаж", "навыки", "технологии"
        ]
        
        found_keywords = []
        text_lower = text.lower()
        
        for keyword in job_keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def extract_job_info(self, screen_data: Dict) -> Dict:
        """
        Извлечение информации о вакансии
        """
        job_info = {
            "position": "",
            "salary_range": "",
            "requirements": [],
            "benefits": [],
            "company_info": ""
        }
        
        text = screen_data.get("text_content", "")
        
        # Поиск позиции
        position_patterns = [
            r"позиция[:\s]+([^\n]+)",
            r"должность[:\s]+([^\n]+)",
            r"position[:\s]+([^\n]+)"
        ]
        
        for pattern in position_patterns:
            import re
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                job_info["position"] = match.group(1).strip()
                break
        
        # Поиск зарплаты
        salary_patterns = [
            r"(\$?\d{1,3}(?:,\d{3})*(?:k|000)?)",
            r"(\d+)\s*(?:k|thousand|тысяч)"
        ]
        
        for pattern in salary_patterns:
            import re
            matches = re.findall(pattern, text)
            if matches:
                job_info["salary_range"] = ", ".join(matches)
                break
        
        return job_info


class MeetingMonitor:
    """
    Монитор встречи в реальном времени
    """
    
    def __init__(self):
        self.analyzer = ScreenAnalyzer()
        self.is_monitoring = False
        self.last_analysis = None
        
    def start_monitoring(self, interval: float = 2.0):
        """
        Запуск мониторинга экрана
        """
        self.is_monitoring = True
        print("👁️ Начат мониторинг экрана собеседования...")
        
        # TODO: Реализовать мониторинг в отдельном потоке
        # threading.Thread(target=self._monitor_loop, args=(interval,)).start()
    
    def stop_monitoring(self):
        """
        Остановка мониторинга
        """
        self.is_monitoring = False
        print("👁️ Мониторинг экрана остановлен")
    
    def get_current_analysis(self) -> Optional[Dict]:
        """
        Получение текущего анализа экрана
        """
        if not self.is_monitoring:
            return None
        
        try:
            # Захват экрана
            screen = self.analyzer.capture_screen()
            if screen is None:
                return None
            
            # Анализ
            analysis = self.analyzer.analyze_meeting_screen(screen)
            self.last_analysis = analysis
            
            return analysis
            
        except Exception as e:
            print(f"❌ Ошибка мониторинга: {e}")
            return None


# =============== ТЕСТИРОВАНИЕ ===============

def test_computer_vision():
    """
    Тестирование компьютерного зрения
    """
    print("🧪 Тестирование компьютерного зрения...")
    
    # Создаем анализатор
    analyzer = ScreenAnalyzer()
    
    # Захват экрана
    print("📸 Захват экрана...")
    screen = analyzer.capture_screen()
    
    if screen is not None:
        print("✅ Экран захвачен")
        
        # Анализ
        print("🔍 Анализ экрана...")
        analysis = analyzer.analyze_meeting_screen(screen)
        
        print(f"📝 Текст: {analysis['text_content'][:100]}...")
        print(f"👥 Лиц обнаружено: {analysis['faces_detected']}")
        print(f"📊 Презентация: {analysis['is_presentation']}")
        print(f"📄 Документ: {analysis['is_document']}")
        print(f"🔑 Ключевые слова: {analysis['job_keywords']}")
    else:
        print("❌ Не удалось захватить экран")


if __name__ == "__main__":
    test_computer_vision()
