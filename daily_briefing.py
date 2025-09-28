# -*- coding: utf-8 -*-
"""
Ежедневный брифинг - утренние и вечерние сводки
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

try:
    from mail_calendar import MailCalendar
    from job_apis import JobAPIManager
    from memory_palace import MemoryPalace
    from secrets_watchdog import SecretsWatchdogManager
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


@dataclass
class BriefingData:
    """Данные для брифинга"""
    date: str
    time_type: str  # 'morning' или 'evening'
    calendar_events: List[Dict]
    emails_summary: Dict
    job_applications: List[Dict]
    reminders: List[str]
    weather: Optional[Dict] = None
    news_summary: Optional[str] = None


class DailyBriefing:
    """
    Ежедневный брифинг - утренние и вечерние сводки
    """
    
    def __init__(self):
        self.logger = logging.getLogger("DailyBriefing")
        
        # Компоненты
        self.mail_calendar = None
        self.job_api_manager = None
        self.memory_palace = None
        self.secrets_manager = None
        
        # Настройки
        self.config = {
            'morning_time': '08:00',
            'evening_time': '20:00',
            'include_weather': True,
            'include_news': True,
            'max_events': 5,
            'max_emails': 10
        }
        
        # Инициализация компонентов
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if not COMPONENTS_AVAILABLE:
                self.logger.warning("Компоненты недоступны")
                return
            
            # Secrets Manager
            self.secrets_manager = SecretsWatchdogManager()
            
            # Mail Calendar
            self.mail_calendar = MailCalendar()
            
            # Job API Manager
            self.job_api_manager = JobAPIManager()
            
            # Memory Palace
            self.memory_palace = MemoryPalace()
            
            self.logger.info("Компоненты Daily Briefing инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    async def generate_morning_briefing(self) -> BriefingData:
        """Генерация утреннего брифинга"""
        self.logger.info("🌅 Генерация утреннего брифинга...")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Собираем данные
        calendar_events = await self._get_today_events()
        emails_summary = await self._get_emails_summary()
        job_applications = await self._get_job_applications()
        reminders = await self._get_reminders()
        weather = await self._get_weather() if self.config['include_weather'] else None
        news_summary = await self._get_news_summary() if self.config['include_news'] else None
        
        return BriefingData(
            date=today,
            time_type='morning',
            calendar_events=calendar_events,
            emails_summary=emails_summary,
            job_applications=job_applications,
            reminders=reminders,
            weather=weather,
            news_summary=news_summary
        )
    
    async def generate_evening_briefing(self) -> BriefingData:
        """Генерация вечернего брифинга"""
        self.logger.info("🌙 Генерация вечернего брифинга...")
        
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Собираем данные за день
        calendar_events = await self._get_today_events()
        emails_summary = await self._get_emails_summary()
        job_applications = await self._get_job_applications()
        reminders = await self._get_reminders()
        
        # Вечерние специфичные данные
        daily_summary = await self._get_daily_summary()
        
        return BriefingData(
            date=today,
            time_type='evening',
            calendar_events=calendar_events,
            emails_summary=emails_summary,
            job_applications=job_applications,
            reminders=reminders,
            weather=None,
            news_summary=daily_summary
        )
    
    async def _get_today_events(self) -> List[Dict]:
        """Получение событий на сегодня"""
        try:
            if not self.mail_calendar:
                return []
            
            events = await self.mail_calendar.get_today_events()
            return events[:self.config['max_events']]
            
        except Exception as e:
            self.logger.error(f"Ошибка получения событий: {e}")
            return []
    
    async def _get_emails_summary(self) -> Dict:
        """Сводка по почте"""
        try:
            if not self.mail_calendar:
                return {"unread": 0, "important": 0, "pending": 0}
            
            emails = await self.mail_calendar.check_emails()
            
            unread = len([e for e in emails if not e.get('read', False)])
            important = len([e for e in emails if e.get('important', False)])
            pending = len([e for e in emails if e.get('pending_reply', False)])
            
            return {
                "unread": unread,
                "important": important,
                "pending": pending,
                "total": len(emails)
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки почты: {e}")
            return {"unread": 0, "important": 0, "pending": 0, "total": 0}
    
    async def _get_job_applications(self) -> List[Dict]:
        """Получение заявок на работу"""
        try:
            if not self.job_api_manager:
                return []
            
            # Получаем последние заявки
            applications = await self.job_api_manager.get_recent_applications()
            return applications[:5]
            
        except Exception as e:
            self.logger.error(f"Ошибка получения заявок: {e}")
            return []
    
    async def _get_reminders(self) -> List[str]:
        """Получение напоминаний"""
        try:
            if not self.memory_palace:
                return []
            
            # Получаем напоминания из памяти
            reminders = await self.memory_palace.get_reminders()
            return reminders[:5]
            
        except Exception as e:
            self.logger.error(f"Ошибка получения напоминаний: {e}")
            return []
    
    async def _get_weather(self) -> Optional[Dict]:
        """Получение погоды"""
        try:
            # Простая заглушка - в реальности можно использовать OpenWeatherMap API
            return {
                "temperature": "22°C",
                "condition": "Ясно",
                "humidity": "65%"
            }
        except Exception as e:
            self.logger.error(f"Ошибка получения погоды: {e}")
            return None
    
    async def _get_news_summary(self) -> Optional[str]:
        """Сводка новостей"""
        try:
            # Простая заглушка - в реальности можно использовать RSS или News API
            return "Главные новости: Технологии, Экономика, Политика"
        except Exception as e:
            self.logger.error(f"Ошибка получения новостей: {e}")
            return None
    
    async def _get_daily_summary(self) -> Optional[str]:
        """Сводка за день"""
        try:
            if not self.memory_palace:
                return "Нет данных за день"
            
            # Получаем сводку активности за день
            summary = await self.memory_palace.get_daily_summary()
            return summary
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки за день: {e}")
            return "Ошибка получения сводки"
    
    def format_briefing(self, briefing: BriefingData) -> str:
        """Форматирование брифинга для отправки"""
        time_emoji = "🌅" if briefing.time_type == 'morning' else "🌙"
        time_text = "Утренний" if briefing.time_type == 'morning' else "Вечерний"
        
        text = f"{time_emoji} <b>{time_text} брифинг</b>\n"
        text += f"📅 {briefing.date}\n\n"
        
        # Календарь
        if briefing.calendar_events:
            text += "📅 <b>События на сегодня:</b>\n"
            for event in briefing.calendar_events:
                text += f"• {event.get('title', 'Без названия')} в {event.get('time', 'не указано')}\n"
            text += "\n"
        
        # Почта
        if briefing.emails_summary:
            text += "📧 <b>Почта:</b>\n"
            text += f"• Непрочитанных: {briefing.emails_summary.get('unread', 0)}\n"
            text += f"• Важных: {briefing.emails_summary.get('important', 0)}\n"
            text += f"• Ожидают ответа: {briefing.emails_summary.get('pending', 0)}\n\n"
        
        # Заявки на работу
        if briefing.job_applications:
            text += "💼 <b>Заявки на работу:</b>\n"
            for app in briefing.job_applications:
                text += f"• {app.get('company', 'Компания')} - {app.get('status', 'Статус')}\n"
            text += "\n"
        
        # Напоминания
        if briefing.reminders:
            text += "🔔 <b>Напоминания:</b>\n"
            for reminder in briefing.reminders:
                text += f"• {reminder}\n"
            text += "\n"
        
        # Погода (только утром)
        if briefing.weather and briefing.time_type == 'morning':
            text += f"🌤️ <b>Погода:</b> {briefing.weather.get('temperature', 'N/A')}, {briefing.weather.get('condition', 'N/A')}\n\n"
        
        # Новости/сводка
        if briefing.news_summary:
            if briefing.time_type == 'morning':
                text += f"📰 <b>Новости:</b> {briefing.news_summary}\n\n"
            else:
                text += f"📊 <b>Сводка за день:</b> {briefing.news_summary}\n\n"
        
        text += "🤖 <i>Сгенерировано МАГА AI</i>"
        
        return text
    
    async def send_briefing(self, briefing: BriefingData, chat_id: int = None):
        """Отправка брифинга"""
        try:
            formatted_text = self.format_briefing(briefing)
            
            # Здесь можно добавить отправку в Telegram
            # или отображение в Windows overlay
            
            self.logger.info(f"Брифинг {briefing.time_type} отправлен")
            return formatted_text
            
        except Exception as e:
            self.logger.error(f"Ошибка отправки брифинга: {e}")
            return None


# Функция для тестирования
async def test_briefing():
    """Тестирование брифинга"""
    briefing = DailyBriefing()
    
    # Утренний брифинг
    morning = await briefing.generate_morning_briefing()
    print("🌅 Утренний брифинг:")
    print(briefing.format_briefing(morning))
    
    print("\n" + "="*50 + "\n")
    
    # Вечерний брифинг
    evening = await briefing.generate_evening_briefing()
    print("🌙 Вечерний брифинг:")
    print(briefing.format_briefing(evening))


if __name__ == "__main__":
    asyncio.run(test_briefing())
