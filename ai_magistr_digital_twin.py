# -*- coding: utf-8 -*-
"""
AI МАГИСТР - Цифровой двойник для собеседований
Главный файл интеграции всех модулей
"""

import asyncio
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional

# Импорт модулей
from gigachat_integration import AIMagistrBrain
from computer_vision import MeetingMonitor
from job_search_api import NegotiationAssistant


class DigitalTwin:
    """
    Главный класс цифрового двойника AI МАГИСТР
    """
    
    def __init__(self, giga_chat_api_key: str):
        # Модули
        self.brain = AIMagistrBrain(giga_chat_api_key)
        self.vision = MeetingMonitor()
        self.negotiator = NegotiationAssistant()
        
        # Состояние
        self.is_active = False
        self.current_interview = None
        self.conversation_context = []
        self.salary_target = 200000
        
        # Настройки
        self.auto_response_enabled = True
        self.vision_monitoring_enabled = True
        self.negotiation_mode = "aggressive"
        
    def start_interview_session(self, job_info: Dict):
        """
        Запуск сессии собеседования
        """
        try:
            self.current_interview = job_info
            self.is_active = True
            
            # Подготовка к переговорам
            negotiation_plan = self.negotiator.prepare_negotiation(
                job_info.get("position", "Developer"),
                self.salary_target
            )
            
            # Запуск мониторинга экрана
            if self.vision_monitoring_enabled:
                self.vision.start_monitoring()
            
            print("🤖 AI МАГИСТР активирован!")
            print(f"💰 Целевая зарплата: ${self.salary_target:,}")
            print(f"🎯 Стратегия: {negotiation_plan.get('strategy', 'aggressive')}")
            print(f"📊 Переговорная сила: {negotiation_plan.get('negotiation_power', {}).get('negotiation_strength', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка запуска сессии: {e}")
            return False
    
    def stop_interview_session(self):
        """
        Остановка сессии
        """
        try:
            self.is_active = False
            self.vision.stop_monitoring()
            
            # Сохранение результатов
            self._save_session_results()
            
            print("🤖 AI МАГИСТР деактивирован")
            print(f"📝 Сохранено {len(self.conversation_context)} взаимодействий")
            
        except Exception as e:
            print(f"❌ Ошибка остановки сессии: {e}")
    
    def process_hr_message(self, message: str) -> str:
        """
        Обработка сообщения HR
        """
        if not self.is_active:
            return ""
        
        try:
            # Анализ экрана (если включен)
            screen_context = {}
            if self.vision_monitoring_enabled:
                screen_analysis = self.vision.get_current_analysis()
                if screen_analysis:
                    screen_context = {
                        "text_content": screen_analysis.get("text_content", ""),
                        "job_keywords": screen_analysis.get("job_keywords", []),
                        "is_presentation": screen_analysis.get("is_presentation", False)
                    }
            
            # Подготовка контекста
            context = {
                "message": message,
                "screen_context": screen_context,
                "interview_info": self.current_interview,
                "salary_target": self.salary_target,
                "conversation_history": self.conversation_context[-5:]  # Последние 5 сообщений
            }
            
            # Генерация ответа через мозг
            response = self.brain.analyze_hr_message(message, context)
            
            # Сохранение в контекст
            self.conversation_context.append({
                "timestamp": datetime.now().isoformat(),
                "hr_message": message,
                "ai_response": response,
                "context": context
            })
            
            return response
            
        except Exception as e:
            print(f"❌ Ошибка обработки сообщения: {e}")
            return "Извините, произошла ошибка."
    
    def get_negotiation_advice(self, hr_offer: int) -> Dict:
        """
        Получение совета по переговорам
        """
        try:
            if not self.current_interview:
                return {}
            
            # Анализ предложения HR
            counter_strategy = self.negotiator.get_counter_offer_strategy(
                hr_offer, 
                self.salary_target
            )
            
            # Дополнительные аргументы
            market_data = self.negotiator.job_search.get_market_data(
                self.current_interview.get("position", "Developer")
            )
            
            advice = {
                "hr_offer": hr_offer,
                "target_salary": self.salary_target,
                "difference": self.salary_target - hr_offer,
                "strategy": counter_strategy.get("strategy", "professional"),
                "message": counter_strategy.get("message", ""),
                "market_average": market_data.get("average_salary", 0),
                "negotiation_tips": self._get_negotiation_tips(hr_offer)
            }
            
            return advice
            
        except Exception as e:
            print(f"❌ Ошибка получения совета: {e}")
            return {}
    
    def _get_negotiation_tips(self, hr_offer: int) -> List[str]:
        """
        Получение советов по переговорам
        """
        tips = []
        
        if hr_offer < self.salary_target * 0.8:
            tips.append("Предложение слишком низкое - используйте агрессивную тактику")
            tips.append("Упомяните о других предложениях")
        elif hr_offer < self.salary_target:
            tips.append("Близко к цели - можно договориться")
            tips.append("Спросите про equity и бонусы")
        else:
            tips.append("Отличное предложение!")
            tips.append("Можете просить еще больше")
        
        return tips
    
    def _save_session_results(self):
        """
        Сохранение результатов сессии
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"interview_session_{timestamp}.json"
            
            results = {
                "session_info": {
                    "start_time": self.conversation_context[0]["timestamp"] if self.conversation_context else None,
                    "end_time": datetime.now().isoformat(),
                    "job_info": self.current_interview,
                    "salary_target": self.salary_target
                },
                "conversation": self.conversation_context,
                "summary": self._generate_session_summary()
            }
            
            import json
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"💾 Результаты сохранены в {filename}")
            
        except Exception as e:
            print(f"❌ Ошибка сохранения результатов: {e}")
    
    def _generate_session_summary(self) -> Dict:
        """
        Генерация сводки сессии
        """
        if not self.conversation_context:
            return {}
        
        total_messages = len(self.conversation_context)
        salary_mentioned = any("зарплата" in msg["hr_message"].lower() or "salary" in msg["hr_message"].lower() 
                             for msg in self.conversation_context)
        
        return {
            "total_interactions": total_messages,
            "salary_discussed": salary_mentioned,
            "ai_personality": self.negotiation_mode,
            "success_indicators": {
                "hr_engaged": total_messages > 5,
                "salary_negotiation": salary_mentioned,
                "technical_discussion": any("python" in msg["hr_message"].lower() 
                                          for msg in self.conversation_context)
            }
        }
    
    def get_status(self) -> Dict:
        """
        Получение статуса цифрового двойника
        """
        return {
            "is_active": self.is_active,
            "current_interview": self.current_interview,
            "conversation_count": len(self.conversation_context),
            "salary_target": self.salary_target,
            "negotiation_mode": self.negotiation_mode,
            "vision_monitoring": self.vision_monitoring_enabled,
            "auto_response": self.auto_response_enabled
        }


# =============== ИНТЕГРАЦИЯ С ОСНОВНОЙ УТИЛИТОЙ ===============

class DigitalTwinIntegration:
    """
    Интеграция цифрового двойника с основной утилитой
    """
    
    def __init__(self, giga_chat_api_key: str):
        self.digital_twin = DigitalTwin(giga_chat_api_key)
        self.is_integrated = False
        
    def integrate_with_ghost_assistant(self, ghost_assistant):
        """
        Интеграция с Ghost Assistant
        """
        try:
            # Переопределяем метод analyze_hr_message
            original_analyze = ghost_assistant.analyze_hr_message
            
            def enhanced_analyze(message: str) -> str:
                # Используем цифровой двойник
                if self.digital_twin.is_active:
                    return self.digital_twin.process_hr_message(message)
                else:
                    return original_analyze(message)
            
            ghost_assistant.analyze_hr_message = enhanced_analyze
            self.is_integrated = True
            
            print("🔗 Цифровой двойник интегрирован с Ghost Assistant")
            
        except Exception as e:
            print(f"❌ Ошибка интеграции: {e}")
    
    def start_digital_twin_session(self, job_info: Dict):
        """
        Запуск сессии цифрового двойника
        """
        return self.digital_twin.start_interview_session(job_info)
    
    def stop_digital_twin_session(self):
        """
        Остановка сессии цифрового двойника
        """
        self.digital_twin.stop_interview_session()


# =============== ТЕСТИРОВАНИЕ ===============

def test_digital_twin():
    """
    Тестирование цифрового двойника
    """
    print("🧪 Тестирование цифрового двойника AI МАГИСТР...")
    
    # Создаем цифровой двойник
    digital_twin = DigitalTwin("test_api_key")
    
    # Тестовая информация о работе
    job_info = {
        "position": "Senior Python Developer",
        "company": "TechCorp",
        "location": "Remote",
        "description": "AI/ML team lead position"
    }
    
    # Запуск сессии
    print("🚀 Запуск сессии...")
    digital_twin.start_interview_session(job_info)
    
    # Тестовые сообщения HR
    test_messages = [
        "Расскажите о вашем опыте с Python",
        "Какая у вас зарплата?",
        "Мы предлагаем $150k",
        "Почему вы хотите работать у нас?",
        "Какие у вас вопросы?"
    ]
    
    # Обработка сообщений
    for message in test_messages:
        print(f"\n👤 HR: {message}")
        response = digital_twin.process_hr_message(message)
        print(f"🤖 AI МАГИСТР: {response}")
    
    # Тест совета по переговорам
    print("\n💰 Совет по переговорам:")
    advice = digital_twin.get_negotiation_advice(150000)
    print(f"Стратегия: {advice.get('strategy', 'unknown')}")
    print(f"Сообщение: {advice.get('message', '')}")
    
    # Остановка сессии
    digital_twin.stop_interview_session()
    
    # Статус
    status = digital_twin.get_status()
    print(f"\n📊 Статус: {status}")


if __name__ == "__main__":
    test_digital_twin()
