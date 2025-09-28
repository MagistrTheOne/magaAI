# -*- coding: utf-8 -*-
"""
Дополнительные фичи для рутины
"""

import asyncio
import json
import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging
import feedparser
import schedule
import time
import threading

try:
    from memory_palace import MemoryPalace
    from brain.gigachat_sdk import BrainManager
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


@dataclass
class LearningItem:
    """Элемент обучения"""
    title: str
    url: str
    summary: str
    category: str
    difficulty: str
    time_to_read: int  # минуты
    tags: List[str]


@dataclass
class BillReminder:
    """Напоминание о счете"""
    id: str
    title: str
    amount: float
    due_date: str
    category: str
    paid: bool = False
    source: str = "email"


@dataclass
class FollowUpTask:
    """Задача follow-up"""
    id: str
    contact: str
    action: str
    due_date: str
    priority: int
    completed: bool = False


class FileOrganizer:
    """
    Организатор файлов - автосортировка Downloads/резюме
    """
    
    def __init__(self):
        self.logger = logging.getLogger("FileOrganizer")
        
        # Папки для сортировки
        self.downloads_path = os.path.expanduser("~/Downloads")
        self.resumes_path = os.path.expanduser("~/Documents/Резюме")
        self.presentations_path = os.path.expanduser("~/Documents/Презентации")
        
        # Правила сортировки
        self.sorting_rules = {
            'resumes': ['.pdf', '.doc', '.docx'],
            'presentations': ['.pptx', '.ppt', '.key'],
            'images': ['.jpg', '.jpeg', '.png', '.gif', '.svg'],
            'documents': ['.pdf', '.txt', '.rtf'],
            'archives': ['.zip', '.rar', '.7z', '.tar', '.gz']
        }
    
    async def organize_downloads(self):
        """Организация папки Downloads"""
        try:
            if not os.path.exists(self.downloads_path):
                self.logger.warning("Папка Downloads не найдена")
                return
            
            files = os.listdir(self.downloads_path)
            organized_count = 0
            
            for file in files:
                file_path = os.path.join(self.downloads_path, file)
                if os.path.isfile(file_path):
                    # Определяем категорию файла
                    category = self._get_file_category(file)
                    
                    if category:
                        # Создаем папку если не существует
                        category_path = os.path.join(self.downloads_path, category)
                        os.makedirs(category_path, exist_ok=True)
                        
                        # Перемещаем файл
                        new_path = os.path.join(category_path, file)
                        shutil.move(file_path, new_path)
                        organized_count += 1
                        self.logger.info(f"Перемещен {file} в {category}")
            
            self.logger.info(f"Организовано {organized_count} файлов")
            
        except Exception as e:
            self.logger.error(f"Ошибка организации файлов: {e}")
    
    def _get_file_category(self, filename: str) -> Optional[str]:
        """Определение категории файла"""
        filename_lower = filename.lower()
        
        for category, extensions in self.sorting_rules.items():
            for ext in extensions:
                if filename_lower.endswith(ext):
                    return category
        
        return None
    
    async def organize_resumes(self):
        """Организация резюме"""
        try:
            if not os.path.exists(self.resumes_path):
                os.makedirs(self.resumes_path, exist_ok=True)
            
            # Создаем подпапки по датам
            current_year = datetime.now().year
            year_path = os.path.join(self.resumes_path, str(current_year))
            os.makedirs(year_path, exist_ok=True)
            
            # Переименовываем файлы по шаблону
            for file in os.listdir(self.downloads_path):
                if any(file.lower().endswith(ext) for ext in ['.pdf', '.doc', '.docx']):
                    if 'резюме' in file.lower() or 'cv' in file.lower():
                        # Переименовываем по шаблону
                        new_name = f"Резюме_{datetime.now().strftime('%Y%m%d')}_{file}"
                        old_path = os.path.join(self.downloads_path, file)
                        new_path = os.path.join(year_path, new_name)
                        shutil.move(old_path, new_path)
                        self.logger.info(f"Организовано резюме: {new_name}")
            
        except Exception as e:
            self.logger.error(f"Ошибка организации резюме: {e}")


class LearningFeed:
    """
    Учебный поток - RSS, TL;DR, SRS карточки
    """
    
    def __init__(self):
        self.logger = logging.getLogger("LearningFeed")
        
        # Компоненты
        self.memory_palace = None
        self.brain_manager = None
        
        # RSS источники
        self.rss_feeds = [
            "https://habr.com/ru/rss/hub/python/",
            "https://habr.com/ru/rss/hub/machine_learning/",
            "https://medium.com/feed/tag/python",
            "https://dev.to/feed"
        ]
        
        # SRS карточки
        self.srs_cards = []
        
        # Инициализация компонентов
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if not COMPONENTS_AVAILABLE:
                self.logger.warning("Компоненты недоступны")
                return
            
            # Memory Palace
            self.memory_palace = MemoryPalace()
            
            # Brain Manager
            self.brain_manager = BrainManager()
            
            self.logger.info("Компоненты Learning Feed инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    async def fetch_learning_content(self) -> List[LearningItem]:
        """Получение учебного контента"""
        try:
            learning_items = []
            
            for feed_url in self.rss_feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    
                    for entry in feed.entries[:5]:  # Берем последние 5 статей
                        # Генерируем TL;DR
                        summary = await self._generate_tldr(entry.title, entry.summary)
                        
                        # Определяем категорию и сложность
                        category = self._categorize_content(entry.title, entry.summary)
                        difficulty = self._assess_difficulty(entry.title, entry.summary)
                        
                        # Оцениваем время чтения
                        time_to_read = self._estimate_reading_time(entry.summary)
                        
                        item = LearningItem(
                            title=entry.title,
                            url=entry.link,
                            summary=summary,
                            category=category,
                            difficulty=difficulty,
                            time_to_read=time_to_read,
                            tags=self._extract_tags(entry.title, entry.summary)
                        )
                        
                        learning_items.append(item)
                        
                except Exception as e:
                    self.logger.error(f"Ошибка парсинга RSS {feed_url}: {e}")
            
            # Сортируем по релевантности
            learning_items.sort(key=lambda x: self._calculate_relevance_score(x), reverse=True)
            
            return learning_items[:10]  # Топ 10 статей
            
        except Exception as e:
            self.logger.error(f"Ошибка получения учебного контента: {e}")
            return []
    
    async def _generate_tldr(self, title: str, content: str) -> str:
        """Генерация TL;DR"""
        try:
            if not self.brain_manager:
                return f"TL;DR: {title}"
            
            prompt = f"Создай краткое изложение статьи '{title}': {content[:500]}"
            tldr = await self.brain_manager.generate_response(prompt)
            
            return tldr[:200] + "..." if len(tldr) > 200 else tldr
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации TL;DR: {e}")
            return f"TL;DR: {title}"
    
    def _categorize_content(self, title: str, content: str) -> str:
        """Категоризация контента"""
        text = f"{title} {content}".lower()
        
        if any(word in text for word in ['python', 'django', 'flask', 'fastapi']):
            return 'Python'
        elif any(word in text for word in ['ml', 'machine learning', 'ai', 'neural']):
            return 'Machine Learning'
        elif any(word in text for word in ['web', 'frontend', 'react', 'vue']):
            return 'Web Development'
        elif any(word in text for word in ['devops', 'docker', 'kubernetes', 'ci/cd']):
            return 'DevOps'
        else:
            return 'General'
    
    def _assess_difficulty(self, title: str, content: str) -> str:
        """Оценка сложности"""
        text = f"{title} {content}".lower()
        
        if any(word in text for word in ['beginner', 'tutorial', 'introduction', 'basics']):
            return 'Beginner'
        elif any(word in text for word in ['advanced', 'expert', 'complex', 'optimization']):
            return 'Advanced'
        else:
            return 'Intermediate'
    
    def _estimate_reading_time(self, content: str) -> int:
        """Оценка времени чтения"""
        words = len(content.split())
        return max(1, words // 200)  # 200 слов в минуту
    
    def _extract_tags(self, title: str, content: str) -> List[str]:
        """Извлечение тегов"""
        text = f"{title} {content}".lower()
        tags = []
        
        tech_keywords = ['python', 'javascript', 'react', 'vue', 'docker', 'kubernetes', 'aws', 'ml', 'ai']
        for keyword in tech_keywords:
            if keyword in text:
                tags.append(keyword)
        
        return tags[:5]  # Максимум 5 тегов
    
    def _calculate_relevance_score(self, item: LearningItem) -> float:
        """Расчет релевантности"""
        score = 0.0
        
        # Приоритет по категориям
        category_scores = {
            'Python': 1.0,
            'Machine Learning': 0.9,
            'Web Development': 0.8,
            'DevOps': 0.7,
            'General': 0.5
        }
        score += category_scores.get(item.category, 0.5)
        
        # Приоритет по сложности
        difficulty_scores = {
            'Beginner': 0.6,
            'Intermediate': 1.0,
            'Advanced': 0.8
        }
        score += difficulty_scores.get(item.difficulty, 0.5)
        
        # Время чтения (предпочитаем средние статьи)
        if 5 <= item.time_to_read <= 15:
            score += 0.3
        elif item.time_to_read < 5:
            score += 0.1
        
        return score
    
    async def create_srs_card(self, learning_item: LearningItem) -> str:
        """Создание SRS карточки"""
        try:
            card_id = f"srs_{len(self.srs_cards) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            card = {
                'id': card_id,
                'title': learning_item.title,
                'url': learning_item.url,
                'summary': learning_item.summary,
                'category': learning_item.category,
                'difficulty': learning_item.difficulty,
                'created_at': datetime.now().isoformat(),
                'next_review': datetime.now().isoformat(),
                'interval_days': 1,
                'ease_factor': 2.5,
                'repetitions': 0
            }
            
            self.srs_cards.append(card)
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"SRS карточка создана: {learning_item.title}",
                    metadata={
                        'type': 'srs_card',
                        'card_id': card_id,
                        'category': learning_item.category,
                        'difficulty': learning_item.difficulty
                    }
                )
            
            return card_id
            
        except Exception as e:
            self.logger.error(f"Ошибка создания SRS карточки: {e}")
            return None
    
    async def get_due_cards(self) -> List[Dict]:
        """Получение карточек для повторения"""
        now = datetime.now()
        due_cards = []
        
        for card in self.srs_cards:
            next_review = datetime.fromisoformat(card['next_review'])
            if next_review <= now:
                due_cards.append(card)
        
        return due_cards
    
    def format_learning_item(self, item: LearningItem) -> str:
        """Форматирование элемента обучения"""
        text = f"📚 <b>{item.title}</b>\n\n"
        text += f"📝 {item.summary}\n\n"
        text += f"🏷️ Категория: {item.category}\n"
        text += f"📊 Сложность: {item.difficulty}\n"
        text += f"⏱️ Время чтения: {item.time_to_read} мин\n"
        text += f"🔗 <a href='{item.url}'>Читать</a>\n"
        
        if item.tags:
            text += f"🏷️ Теги: {', '.join(item.tags)}\n"
        
        return text


class BillReminderManager:
    """
    Менеджер напоминаний о счетах
    """
    
    def __init__(self):
        self.logger = logging.getLogger("BillReminderManager")
        
        # Компоненты
        self.memory_palace = None
        
        # Напоминания
        self.bill_reminders = []
        
        # Инициализация компонентов
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if not COMPONENTS_AVAILABLE:
                self.logger.warning("Компоненты недоступны")
                return
            
            # Memory Palace
            self.memory_palace = MemoryPalace()
            
            self.logger.info("Компоненты Bill Reminder Manager инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    async def extract_bills_from_emails(self) -> List[BillReminder]:
        """Извлечение счетов из писем"""
        try:
            # Здесь должна быть интеграция с почтой
            # Пока заглушка
            bills = [
                BillReminder(
                    id="bill_1",
                    title="Интернет провайдер",
                    amount=1500.0,
                    due_date=(datetime.now() + timedelta(days=5)).isoformat(),
                    category="Интернет",
                    source="email"
                ),
                BillReminder(
                    id="bill_2",
                    title="Электричество",
                    amount=2500.0,
                    due_date=(datetime.now() + timedelta(days=10)).isoformat(),
                    category="Коммунальные",
                    source="email"
                )
            ]
            
            self.bill_reminders.extend(bills)
            
            # Сохраняем в память
            if self.memory_palace:
                for bill in bills:
                    await self.memory_palace.add_memory(
                        content=f"Счет: {bill.title} - {bill.amount} руб до {bill.due_date}",
                        metadata={
                            'type': 'bill_reminder',
                            'bill_id': bill.id,
                            'amount': bill.amount,
                            'due_date': bill.due_date,
                            'category': bill.category
                        }
                    )
            
            return bills
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения счетов: {e}")
            return []
    
    async def get_upcoming_bills(self, days_ahead: int = 7) -> List[BillReminder]:
        """Получение предстоящих счетов"""
        try:
            cutoff_date = datetime.now() + timedelta(days=days_ahead)
            upcoming_bills = []
            
            for bill in self.bill_reminders:
                if not bill.paid:
                    due_date = datetime.fromisoformat(bill.due_date)
                    if due_date <= cutoff_date:
                        upcoming_bills.append(bill)
            
            return sorted(upcoming_bills, key=lambda x: x.due_date)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения предстоящих счетов: {e}")
            return []
    
    def format_bill_reminder(self, bill: BillReminder) -> str:
        """Форматирование напоминания о счете"""
        due_date = datetime.fromisoformat(bill.due_date)
        days_left = (due_date - datetime.now()).days
        
        text = f"💰 <b>{bill.title}</b>\n"
        text += f"💵 Сумма: {bill.amount} руб\n"
        text += f"📅 Срок: {due_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Осталось: {days_left} дней\n"
        text += f"🏷️ Категория: {bill.category}\n"
        
        if days_left <= 3:
            text += "⚠️ <b>СРОЧНО!</b>\n"
        elif days_left <= 7:
            text += "🔔 <b>Скоро срок</b>\n"
        
        return text


class FollowUpPlanner:
    """
    Планировщик follow-up
    """
    
    def __init__(self):
        self.logger = logging.getLogger("FollowUpPlanner")
        
        # Компоненты
        self.memory_palace = None
        
        # Задачи follow-up
        self.follow_up_tasks = []
        
        # Инициализация компонентов
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if not COMPONENTS_AVAILABLE:
                self.logger.warning("Компоненты недоступны")
                return
            
            # Memory Palace
            self.memory_palace = MemoryPalace()
            
            self.logger.info("Компоненты Follow-up Planner инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    async def create_follow_up(self, contact: str, action: str, due_date: str, priority: int = 3) -> str:
        """Создание follow-up задачи"""
        try:
            task_id = f"followup_{len(self.follow_up_tasks) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            task = FollowUpTask(
                id=task_id,
                contact=contact,
                action=action,
                due_date=due_date,
                priority=priority
            )
            
            self.follow_up_tasks.append(task)
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"Follow-up задача: {action} для {contact} до {due_date}",
                    metadata={
                        'type': 'followup_task',
                        'task_id': task_id,
                        'contact': contact,
                        'action': action,
                        'due_date': due_date,
                        'priority': priority
                    }
                )
            
            self.logger.info(f"Создана follow-up задача: {task_id}")
            return task_id
            
        except Exception as e:
            self.logger.error(f"Ошибка создания follow-up задачи: {e}")
            return None
    
    async def get_due_follow_ups(self) -> List[FollowUpTask]:
        """Получение просроченных follow-up задач"""
        try:
            now = datetime.now()
            due_tasks = []
            
            for task in self.follow_up_tasks:
                if not task.completed:
                    due_date = datetime.fromisoformat(task.due_date)
                    if due_date <= now:
                        due_tasks.append(task)
            
            return sorted(due_tasks, key=lambda x: (x.priority, x.due_date), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения просроченных задач: {e}")
            return []
    
    async def complete_follow_up(self, task_id: str) -> bool:
        """Завершение follow-up задачи"""
        try:
            for task in self.follow_up_tasks:
                if task.id == task_id:
                    task.completed = True
                    
                    # Сохраняем в память
                    if self.memory_palace:
                        await self.memory_palace.add_memory(
                            content=f"Завершена follow-up задача: {task.action} для {task.contact}",
                            metadata={
                                'type': 'followup_completed',
                                'task_id': task_id,
                                'contact': task.contact,
                                'action': task.action
                            }
                        )
                    
                    self.logger.info(f"Завершена follow-up задача: {task_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Ошибка завершения follow-up задачи: {e}")
            return False
    
    def format_follow_up_task(self, task: FollowUpTask) -> str:
        """Форматирование follow-up задачи"""
        due_date = datetime.fromisoformat(task.due_date)
        days_left = (due_date - datetime.now()).days
        
        text = f"📞 <b>Follow-up: {task.contact}</b>\n"
        text += f"📝 Действие: {task.action}\n"
        text += f"📅 Срок: {due_date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Осталось: {days_left} дней\n"
        text += f"⭐ Приоритет: {task.priority}/5\n"
        
        if days_left < 0:
            text += "⚠️ <b>ПРОСРОЧЕНО!</b>\n"
        elif days_left <= 1:
            text += "🔔 <b>Сегодня!</b>\n"
        
        return text


class WellbeingReminder:
    """
    Напоминания о здоровье и микропаузах
    """
    
    def __init__(self):
        self.logger = logging.getLogger("WellbeingReminder")
        
        # Настройки
        self.config = {
            'break_interval': 25,  # минуты
            'water_reminder': 60,  # минуты
            'stretch_reminder': 120,  # минуты
            'eye_rest_reminder': 30  # минуты
        }
        
        # Состояние
        self.last_break = datetime.now()
        self.last_water = datetime.now()
        self.last_stretch = datetime.now()
        self.last_eye_rest = datetime.now()
    
    async def check_reminders(self) -> List[str]:
        """Проверка напоминаний"""
        try:
            reminders = []
            now = datetime.now()
            
            # Проверка перерыва
            if (now - self.last_break).total_seconds() >= self.config['break_interval'] * 60:
                reminders.append("☕ Время для перерыва! Отдохните 5 минут")
                self.last_break = now
            
            # Проверка воды
            if (now - self.last_water).total_seconds() >= self.config['water_reminder'] * 60:
                reminders.append("💧 Время выпить воды! Оставайтесь гидратированными")
                self.last_water = now
            
            # Проверка растяжки
            if (now - self.last_stretch).total_seconds() >= self.config['stretch_reminder'] * 60:
                reminders.append("🤸 Время для растяжки! Разомнитесь")
                self.last_stretch = now
            
            # Проверка отдыха глаз
            if (now - self.last_eye_rest).total_seconds() >= self.config['eye_rest_reminder'] * 60:
                reminders.append("👁️ Отдохните глаза! Посмотрите вдаль 20 секунд")
                self.last_eye_rest = now
            
            return reminders
            
        except Exception as e:
            self.logger.error(f"Ошибка проверки напоминаний: {e}")
            return []
    
    def format_reminder(self, reminder: str) -> str:
        """Форматирование напоминания"""
        return f"🌱 <b>Напоминание о здоровье</b>\n\n{reminder}\n\n💚 Заботьтесь о себе!"


# Функция для тестирования
async def test_routine_features():
    """Тестирование дополнительных фич"""
    print("🧪 Тестирование дополнительных фич рутины...")
    
    # Тест File Organizer
    organizer = FileOrganizer()
    await organizer.organize_downloads()
    print("✅ File Organizer протестирован")
    
    # Тест Learning Feed
    learning = LearningFeed()
    items = await learning.fetch_learning_content()
    print(f"✅ Learning Feed: получено {len(items)} статей")
    
    # Тест Bill Reminder
    bill_manager = BillReminderManager()
    bills = await bill_manager.extract_bills_from_emails()
    print(f"✅ Bill Reminder: найдено {len(bills)} счетов")
    
    # Тест Follow-up Planner
    followup = FollowUpPlanner()
    task_id = await followup.create_follow_up(
        contact="hr@company.com",
        action="Отправить резюме",
        due_date=(datetime.now() + timedelta(days=1)).isoformat()
    )
    print(f"✅ Follow-up Planner: создана задача {task_id}")
    
    # Тест Wellbeing Reminder
    wellbeing = WellbeingReminder()
    reminders = await wellbeing.check_reminders()
    print(f"✅ Wellbeing Reminder: {len(reminders)} напоминаний")
    
    print("🎉 Все тесты завершены!")


if __name__ == "__main__":
    asyncio.run(test_routine_features())
