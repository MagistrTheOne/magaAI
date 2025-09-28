# -*- coding: utf-8 -*-
"""
Ассистент встреч - до, во время и после встреч
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import logging
import threading
import time

try:
    from faster_whisper import WhisperModel
    from mail_calendar import MailCalendar
    from memory_palace import MemoryPalace
    from brain.gigachat_sdk import BrainManager
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


@dataclass
class MeetingContext:
    """Контекст встречи"""
    title: str
    participants: List[str]
    company: str
    date: str
    time: str
    duration: int  # минуты
    agenda: List[str]
    previous_emails: List[Dict]
    company_info: Dict[str, Any]
    participant_profiles: Dict[str, Dict]


@dataclass
class MeetingNote:
    """Заметка встречи"""
    timestamp: str
    speaker: str
    content: str
    action_item: bool = False
    important: bool = False


@dataclass
class MeetingSummary:
    """Сводка встречи"""
    key_points: List[str]
    action_items: List[str]
    decisions: List[str]
    next_steps: List[str]
    participants_summary: Dict[str, str]


class MeetingAssistant:
    """
    Ассистент встреч - полный цикл поддержки
    """
    
    def __init__(self):
        self.logger = logging.getLogger("MeetingAssistant")
        
        # Компоненты
        self.mail_calendar = None
        self.memory_palace = None
        self.brain_manager = None
        self.whisper_model = None
        
        # Состояние
        self.current_meeting = None
        self.is_recording = False
        self.notes = []
        self.recording_thread = None
        
        # Настройки
        self.config = {
            'auto_record': True,
            'auto_transcribe': True,
            'save_audio': True,
            'language': 'ru'
        }
        
        # Инициализация компонентов
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if not COMPONENTS_AVAILABLE:
                self.logger.warning("Компоненты недоступны")
                return
            
            # Mail Calendar
            self.mail_calendar = MailCalendar()
            
            # Memory Palace
            self.memory_palace = MemoryPalace()
            
            # Brain Manager
            self.brain_manager = BrainManager()
            
            # Whisper для транскрипции
            self.whisper_model = WhisperModel("base", device="cpu")
            
            self.logger.info("Компоненты Meeting Assistant инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    async def prepare_meeting(self, meeting_id: str) -> MeetingContext:
        """Подготовка к встрече"""
        self.logger.info(f"🔍 Подготовка к встрече {meeting_id}")
        
        try:
            # Получаем данные встречи
            meeting_data = await self._get_meeting_data(meeting_id)
            
            # Собираем контекст
            participants = meeting_data.get('participants', [])
            company = meeting_data.get('company', 'Неизвестно')
            
            # Получаем предыдущие письма
            previous_emails = await self._get_previous_emails(participants, company)
            
            # Информация о компании
            company_info = await self._get_company_info(company)
            
            # Профили участников
            participant_profiles = await self._get_participant_profiles(participants)
            
            context = MeetingContext(
                title=meeting_data.get('title', 'Встреча'),
                participants=participants,
                company=company,
                date=meeting_data.get('date', ''),
                time=meeting_data.get('time', ''),
                duration=meeting_data.get('duration', 60),
                agenda=meeting_data.get('agenda', []),
                previous_emails=previous_emails,
                company_info=company_info,
                participant_profiles=participant_profiles
            )
            
            self.current_meeting = context
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"Подготовка к встрече: {context.title}",
                    metadata={
                        'type': 'meeting_prep',
                        'meeting_id': meeting_id,
                        'company': company,
                        'participants': participants
                    }
                )
            
            return context
            
        except Exception as e:
            self.logger.error(f"Ошибка подготовки к встрече: {e}")
            return None
    
    async def start_meeting(self):
        """Начало встречи"""
        if not self.current_meeting:
            self.logger.error("Нет активной встречи")
            return
        
        self.logger.info("🎤 Начало встречи")
        
        # Начинаем запись
        if self.config['auto_record']:
            await self.start_recording()
        
        # Создаем первую заметку
        note = MeetingNote(
            timestamp=datetime.now().isoformat(),
            speaker="System",
            content="Встреча началась",
            important=True
        )
        self.notes.append(note)
    
    async def start_recording(self):
        """Начало записи"""
        if self.is_recording:
            return
        
        self.is_recording = True
        self.logger.info("🔴 Начало записи встречи")
        
        # Запускаем запись в отдельном потоке
        self.recording_thread = threading.Thread(target=self._recording_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
    
    def _recording_loop(self):
        """Цикл записи"""
        while self.is_recording:
            try:
                # Здесь должна быть реальная запись аудио
                # Пока заглушка
                time.sleep(1)
            except Exception as e:
                self.logger.error(f"Ошибка записи: {e}")
    
    async def stop_recording(self):
        """Остановка записи"""
        if not self.is_recording:
            return
        
        self.is_recording = False
        self.logger.info("⏹️ Остановка записи")
        
        if self.recording_thread:
            self.recording_thread.join()
    
    async def add_note(self, content: str, speaker: str = "User", important: bool = False):
        """Добавление заметки"""
        note = MeetingNote(
            timestamp=datetime.now().isoformat(),
            speaker=speaker,
            content=content,
            important=important
        )
        self.notes.append(note)
        
        self.logger.info(f"📝 Добавлена заметка: {content[:50]}...")
    
    async def transcribe_audio(self, audio_file: str) -> str:
        """Транскрипция аудио"""
        try:
            if not self.whisper_model:
                return "Whisper модель недоступна"
            
            segments, info = self.whisper_model.transcribe(audio_file, language=self.config['language'])
            text = " ".join([segment.text for segment in segments])
            
            return text
            
        except Exception as e:
            self.logger.error(f"Ошибка транскрипции: {e}")
            return ""
    
    async def end_meeting(self) -> MeetingSummary:
        """Завершение встречи"""
        if not self.current_meeting:
            return None
        
        self.logger.info("🏁 Завершение встречи")
        
        # Останавливаем запись
        await self.stop_recording()
        
        # Анализируем заметки
        summary = await self._analyze_notes()
        
        # Сохраняем в память
        if self.memory_palace:
            await self.memory_palace.add_memory(
                content=f"Завершена встреча: {self.current_meeting.title}",
                metadata={
                    'type': 'meeting_summary',
                    'company': self.current_meeting.company,
                    'participants': self.current_meeting.participants,
                    'key_points': summary.key_points,
                    'action_items': summary.action_items
                }
            )
        
        # Очищаем состояние
        self.current_meeting = None
        self.notes = []
        
        return summary
    
    async def _get_meeting_data(self, meeting_id: str) -> Dict:
        """Получение данных встречи"""
        # Заглушка - в реальности получаем из календаря
        return {
            'title': 'Собеседование на позицию Python разработчика',
            'participants': ['hr@company.com', 'tech@company.com'],
            'company': 'Tech Company',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': '14:00',
            'duration': 60,
            'agenda': ['Знакомство', 'Технические вопросы', 'Обсуждение условий']
        }
    
    async def _get_previous_emails(self, participants: List[str], company: str) -> List[Dict]:
        """Получение предыдущих писем"""
        try:
            if not self.mail_calendar:
                return []
            
            # Получаем письма от участников
            emails = []
            for participant in participants:
                participant_emails = await self.mail_calendar.get_emails_from(participant)
                emails.extend(participant_emails)
            
            return emails[:10]  # Последние 10 писем
            
        except Exception as e:
            self.logger.error(f"Ошибка получения писем: {e}")
            return []
    
    async def _get_company_info(self, company: str) -> Dict[str, Any]:
        """Получение информации о компании"""
        try:
            if not self.memory_palace:
                return {}
            
            # Ищем информацию о компании в памяти
            company_memories = await self.memory_palace.search_memories(f"компания {company}")
            
            return {
                'memories': company_memories,
                'last_interaction': 'Недавно',
                'industry': 'IT'
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения информации о компании: {e}")
            return {}
    
    async def _get_participant_profiles(self, participants: List[str]) -> Dict[str, Dict]:
        """Получение профилей участников"""
        profiles = {}
        
        for participant in participants:
            try:
                if self.memory_palace:
                    # Ищем информацию об участнике
                    participant_memories = await self.memory_palace.search_memories(participant)
                    
                    profiles[participant] = {
                        'memories': participant_memories,
                        'role': 'Участник встречи',
                        'last_contact': 'Недавно'
                    }
                else:
                    profiles[participant] = {
                        'role': 'Участник встречи',
                        'last_contact': 'Неизвестно'
                    }
                    
            except Exception as e:
                self.logger.error(f"Ошибка получения профиля {participant}: {e}")
                profiles[participant] = {'role': 'Участник встречи'}
        
        return profiles
    
    async def _analyze_notes(self) -> MeetingSummary:
        """Анализ заметок встречи"""
        if not self.notes:
            return MeetingSummary([], [], [], [], {})
        
        # Извлекаем ключевые моменты
        key_points = []
        action_items = []
        decisions = []
        next_steps = []
        
        for note in self.notes:
            if note.important:
                key_points.append(note.content)
            
            if note.action_item:
                action_items.append(note.content)
            
            # Простой анализ содержания
            if any(word in note.content.lower() for word in ['решили', 'договорились', 'согласовали']):
                decisions.append(note.content)
            
            if any(word in note.content.lower() for word in ['следующий', 'далее', 'потом']):
                next_steps.append(note.content)
        
        # Сводка по участникам
        participants_summary = {}
        for note in self.notes:
            if note.speaker not in participants_summary:
                participants_summary[note.speaker] = []
            participants_summary[note.speaker].append(note.content)
        
        return MeetingSummary(
            key_points=key_points,
            action_items=action_items,
            decisions=decisions,
            next_steps=next_steps,
            participants_summary=participants_summary
        )
    
    def format_meeting_context(self, context: MeetingContext) -> str:
        """Форматирование контекста встречи"""
        text = f"📅 <b>Контекст встречи: {context.title}</b>\n\n"
        text += f"🏢 Компания: {context.company}\n"
        text += f"📅 Дата: {context.date} в {context.time}\n"
        text += f"⏱️ Длительность: {context.duration} мин\n\n"
        
        if context.participants:
            text += f"👥 <b>Участники:</b>\n"
            for participant in context.participants:
                text += f"• {participant}\n"
            text += "\n"
        
        if context.agenda:
            text += f"📋 <b>Повестка:</b>\n"
            for item in context.agenda:
                text += f"• {item}\n"
            text += "\n"
        
        if context.previous_emails:
            text += f"📧 <b>Предыдущие письма:</b> {len(context.previous_emails)}\n"
        
        return text
    
    def format_meeting_summary(self, summary: MeetingSummary) -> str:
        """Форматирование сводки встречи"""
        text = f"📊 <b>Сводка встречи</b>\n\n"
        
        if summary.key_points:
            text += f"🔑 <b>Ключевые моменты:</b>\n"
            for point in summary.key_points:
                text += f"• {point}\n"
            text += "\n"
        
        if summary.action_items:
            text += f"✅ <b>Задачи:</b>\n"
            for item in summary.action_items:
                text += f"• {item}\n"
            text += "\n"
        
        if summary.decisions:
            text += f"🤝 <b>Решения:</b>\n"
            for decision in summary.decisions:
                text += f"• {decision}\n"
            text += "\n"
        
        if summary.next_steps:
            text += f"➡️ <b>Следующие шаги:</b>\n"
            for step in summary.next_steps:
                text += f"• {step}\n"
            text += "\n"
        
        return text


# Функция для тестирования
async def test_meeting_assistant():
    """Тестирование ассистента встреч"""
    assistant = MeetingAssistant()
    
    # Подготовка к встрече
    context = await assistant.prepare_meeting("test_meeting")
    if context:
        print("Контекст встречи:")
        print(assistant.format_meeting_context(context))
    
    # Начало встречи
    await assistant.start_meeting()
    
    # Добавление заметок
    await assistant.add_note("Обсудили технические требования", "User", True)
    await assistant.add_note("Договорились о следующем этапе", "HR", True)
    
    # Завершение встречи
    summary = await assistant.end_meeting()
    if summary:
        print("\nСводка встречи:")
        print(assistant.format_meeting_summary(summary))


if __name__ == "__main__":
    asyncio.run(test_meeting_assistant())
