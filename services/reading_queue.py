# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Очередь чтения: саммари/перевод/карточки
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class ReadingStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PAUSED = "paused"
    ARCHIVED = "archived"

class ReadingType(Enum):
    ARTICLE = "article"
    BOOK = "book"
    PAPER = "paper"
    BLOG_POST = "blog_post"
    NEWS = "news"
    DOCUMENT = "document"
    OTHER = "other"

class CardType(Enum):
    DEFINITION = "definition"
    CONCEPT = "concept"
    FACT = "fact"
    QUOTE = "quote"
    QUESTION = "question"

@dataclass
class ReadingItem:
    id: str
    title: str
    url: str
    content: str
    reading_type: ReadingType
    status: ReadingStatus
    priority: int  # 1-5, где 5 - высший приоритет
    estimated_reading_time: int  # в минутах
    actual_reading_time: Optional[int] = None
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tags: List[str] = None
    notes: str = ""
    summary: str = ""
    translation: str = ""
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.tags is None:
            self.tags = []

@dataclass
class ReadingCard:
    id: str
    reading_item_id: str
    card_type: CardType
    front: str
    back: str
    difficulty: int  # 1-5
    created_at: datetime
    last_reviewed: Optional[datetime] = None
    review_count: int = 0
    correct_count: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class ReadingSession:
    id: str
    reading_item_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    pages_read: int = 0
    words_read: int = 0
    notes: str = ""
    comprehension_score: Optional[int] = None  # 1-10

class ReadingQueueService:
    """Сервис очереди чтения"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.items_file = self.storage_dir / "reading_items.json"
        self.cards_file = self.storage_dir / "reading_cards.json"
        self.sessions_file = self.storage_dir / "reading_sessions.json"
        
        # Загружаем данные
        self.items = self._load_items()
        self.cards = self._load_cards()
        self.sessions = self._load_sessions()
    
    def _load_items(self) -> Dict[str, ReadingItem]:
        """Загрузка элементов чтения из файла"""
        try:
            if self.items_file.exists():
                with open(self.items_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    items = {}
                    for item_id, item_data in data.items():
                        item_data['reading_type'] = ReadingType(item_data['reading_type'])
                        item_data['status'] = ReadingStatus(item_data['status'])
                        item_data['created_at'] = datetime.fromisoformat(item_data['created_at'])
                        if item_data.get('started_at'):
                            item_data['started_at'] = datetime.fromisoformat(item_data['started_at'])
                        if item_data.get('completed_at'):
                            item_data['completed_at'] = datetime.fromisoformat(item_data['completed_at'])
                        items[item_id] = ReadingItem(**item_data)
                    return items
        except Exception as e:
            print(f"Ошибка загрузки элементов чтения: {e}")
        return {}
    
    def _save_items(self):
        """Сохранение элементов чтения в файл"""
        try:
            data = {}
            for item_id, item in self.items.items():
                item_dict = asdict(item)
                item_dict['reading_type'] = item.reading_type.value
                item_dict['status'] = item.status.value
                item_dict['created_at'] = item.created_at.isoformat()
                if item.started_at:
                    item_dict['started_at'] = item.started_at.isoformat()
                if item.completed_at:
                    item_dict['completed_at'] = item.completed_at.isoformat()
                data[item_id] = item_dict
            
            with open(self.items_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения элементов чтения: {e}")
    
    def _load_cards(self) -> Dict[str, ReadingCard]:
        """Загрузка карточек из файла"""
        try:
            if self.cards_file.exists():
                with open(self.cards_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    cards = {}
                    for card_id, card_data in data.items():
                        card_data['card_type'] = CardType(card_data['card_type'])
                        card_data['created_at'] = datetime.fromisoformat(card_data['created_at'])
                        if card_data.get('last_reviewed'):
                            card_data['last_reviewed'] = datetime.fromisoformat(card_data['last_reviewed'])
                        cards[card_id] = ReadingCard(**card_data)
                    return cards
        except Exception as e:
            print(f"Ошибка загрузки карточек: {e}")
        return {}
    
    def _save_cards(self):
        """Сохранение карточек в файл"""
        try:
            data = {}
            for card_id, card in self.cards.items():
                card_dict = asdict(card)
                card_dict['card_type'] = card.card_type.value
                card_dict['created_at'] = card.created_at.isoformat()
                if card.last_reviewed:
                    card_dict['last_reviewed'] = card.last_reviewed.isoformat()
                data[card_id] = card_dict
            
            with open(self.cards_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения карточек: {e}")
    
    def _load_sessions(self) -> Dict[str, ReadingSession]:
        """Загрузка сессий чтения из файла"""
        try:
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions = {}
                    for session_id, session_data in data.items():
                        session_data['start_time'] = datetime.fromisoformat(session_data['start_time'])
                        if session_data.get('end_time'):
                            session_data['end_time'] = datetime.fromisoformat(session_data['end_time'])
                        sessions[session_id] = ReadingSession(**session_data)
                    return sessions
        except Exception as e:
            print(f"Ошибка загрузки сессий чтения: {e}")
        return {}
    
    def _save_sessions(self):
        """Сохранение сессий чтения в файл"""
        try:
            data = {}
            for session_id, session in self.sessions.items():
                session_dict = asdict(session)
                session_dict['start_time'] = session.start_time.isoformat()
                if session.end_time:
                    session_dict['end_time'] = session.end_time.isoformat()
                data[session_id] = session_dict
            
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения сессий чтения: {e}")
    
    def _estimate_reading_time(self, content: str) -> int:
        """Оценка времени чтения (в минутах)"""
        try:
            # Средняя скорость чтения: 200-300 слов в минуту
            words = len(content.split())
            return max(1, words // 250)  # 250 слов в минуту
        except Exception as e:
            print(f"Ошибка оценки времени чтения: {e}")
            return 1
    
    def add_reading_item(self, title: str, url: str, content: str, 
                        reading_type: ReadingType, priority: int = 3,
                        tags: List[str] = None, notes: str = "") -> str:
        """Добавление элемента в очередь чтения"""
        try:
            item_id = str(uuid.uuid4())
            estimated_time = self._estimate_reading_time(content)
            
            item = ReadingItem(
                id=item_id,
                title=title,
                url=url,
                content=content,
                reading_type=reading_type,
                status=ReadingStatus.QUEUED,
                priority=priority,
                estimated_reading_time=estimated_time,
                tags=tags or [],
                notes=notes
            )
            
            self.items[item_id] = item
            self._save_items()
            
            return item_id
            
        except Exception as e:
            print(f"Ошибка добавления элемента чтения: {e}")
            return None
    
    def start_reading(self, item_id: str) -> str:
        """Начало чтения элемента"""
        try:
            if item_id not in self.items:
                return None
            
            item = self.items[item_id]
            item.status = ReadingStatus.IN_PROGRESS
            item.started_at = datetime.now()
            self._save_items()
            
            # Создаем сессию чтения
            session_id = str(uuid.uuid4())
            session = ReadingSession(
                id=session_id,
                reading_item_id=item_id,
                start_time=datetime.now()
            )
            self.sessions[session_id] = session
            self._save_sessions()
            
            return session_id
            
        except Exception as e:
            print(f"Ошибка начала чтения: {e}")
            return None
    
    def complete_reading(self, item_id: str, actual_time: int = None, 
                        summary: str = "", translation: str = "") -> bool:
        """Завершение чтения элемента"""
        try:
            if item_id not in self.items:
                return False
            
            item = self.items[item_id]
            item.status = ReadingStatus.COMPLETED
            item.completed_at = datetime.now()
            if actual_time:
                item.actual_reading_time = actual_time
            if summary:
                item.summary = summary
            if translation:
                item.translation = translation
            
            self._save_items()
            
            # Завершаем активную сессию
            for session in self.sessions.values():
                if (session.reading_item_id == item_id and 
                    session.end_time is None):
                    session.end_time = datetime.now()
                    break
            
            self._save_sessions()
            
            return True
            
        except Exception as e:
            print(f"Ошибка завершения чтения: {e}")
            return False
    
    def create_card(self, reading_item_id: str, card_type: CardType, 
                   front: str, back: str, difficulty: int = 3,
                   tags: List[str] = None) -> str:
        """Создание карточки для повторения"""
        try:
            card_id = str(uuid.uuid4())
            
            card = ReadingCard(
                id=card_id,
                reading_item_id=reading_item_id,
                card_type=card_type,
                front=front,
                back=back,
                difficulty=difficulty,
                created_at=datetime.now(),
                tags=tags or []
            )
            
            self.cards[card_id] = card
            self._save_cards()
            
            return card_id
            
        except Exception as e:
            print(f"Ошибка создания карточки: {e}")
            return None
    
    def review_card(self, card_id: str, correct: bool) -> bool:
        """Повторение карточки"""
        try:
            if card_id not in self.cards:
                return False
            
            card = self.cards[card_id]
            card.last_reviewed = datetime.now()
            card.review_count += 1
            if correct:
                card.correct_count += 1
            
            self._save_cards()
            return True
            
        except Exception as e:
            print(f"Ошибка повторения карточки: {e}")
            return False
    
    def get_reading_queue(self, status: ReadingStatus = None) -> List[ReadingItem]:
        """Получение очереди чтения"""
        try:
            items = list(self.items.values())
            if status:
                items = [i for i in items if i.status == status]
            return sorted(items, key=lambda x: (x.priority, x.created_at), reverse=True)
        except Exception as e:
            print(f"Ошибка получения очереди чтения: {e}")
            return []
    
    def get_cards_for_review(self, limit: int = 10) -> List[ReadingCard]:
        """Получение карточек для повторения"""
        try:
            # Карточки, которые не повторялись более 24 часов
            cutoff_time = datetime.now() - timedelta(hours=24)
            review_cards = []
            
            for card in self.cards.values():
                if (card.last_reviewed is None or 
                    card.last_reviewed < cutoff_time):
                    review_cards.append(card)
            
            # Сортируем по приоритету (сложность и количество повторений)
            review_cards.sort(key=lambda x: (x.difficulty, x.review_count))
            return review_cards[:limit]
            
        except Exception as e:
            print(f"Ошибка получения карточек для повторения: {e}")
            return []
    
    def get_reading_stats(self, item_id: str) -> Dict[str, Any]:
        """Получение статистики чтения элемента"""
        try:
            item = self.items.get(item_id)
            if not item:
                return {}
            
            # Получаем сессии для этого элемента
            sessions = [s for s in self.sessions.values() if s.reading_item_id == item_id]
            total_sessions = len(sessions)
            total_time = sum((s.end_time - s.start_time).total_seconds() / 60 
                           for s in sessions if s.end_time)
            
            # Получаем карточки для этого элемента
            cards = [c for c in self.cards.values() if c.reading_item_id == item_id]
            total_cards = len(cards)
            reviewed_cards = len([c for c in cards if c.review_count > 0])
            
            return {
                'item_id': item_id,
                'title': item.title,
                'status': item.status.value,
                'priority': item.priority,
                'estimated_time': item.estimated_reading_time,
                'actual_time': item.actual_reading_time,
                'total_sessions': total_sessions,
                'total_reading_time': total_time,
                'total_cards': total_cards,
                'reviewed_cards': reviewed_cards,
                'completion_rate': reviewed_cards / max(1, total_cards)
            }
        except Exception as e:
            print(f"Ошибка получения статистики чтения: {e}")
            return {}
    
    def get_weekly_stats(self, start_date: date) -> Dict[str, Any]:
        """Получение недельной статистики чтения"""
        try:
            end_date = start_date + timedelta(days=7)
            weekly_items = [i for i in self.items.values() 
                          if start_date <= i.created_at.date() < end_date]
            
            completed_items = [i for i in weekly_items if i.status == ReadingStatus.COMPLETED]
            total_reading_time = sum(i.actual_reading_time or 0 for i in completed_items)
            
            # Статистика по карточкам
            weekly_cards = [c for c in self.cards.values() 
                          if start_date <= c.created_at.date() < end_date]
            reviewed_cards = [c for c in weekly_cards if c.review_count > 0]
            
            return {
                'week_start': start_date.isoformat(),
                'week_end': end_date.isoformat(),
                'items_added': len(weekly_items),
                'items_completed': len(completed_items),
                'completion_rate': len(completed_items) / max(1, len(weekly_items)),
                'total_reading_time': total_reading_time,
                'cards_created': len(weekly_cards),
                'cards_reviewed': len(reviewed_cards),
                'avg_reading_time': total_reading_time / max(1, len(completed_items))
            }
        except Exception as e:
            print(f"Ошибка получения недельной статистики: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        try:
            total_items = len(self.items)
            completed_items = len([i for i in self.items.values() if i.status == ReadingStatus.COMPLETED])
            total_cards = len(self.cards)
            reviewed_cards = len([c for c in self.cards.values() if c.review_count > 0])
            
            # Статистика по типам
            by_type = {}
            for item in self.items.values():
                item_type = item.reading_type.value
                if item_type not in by_type:
                    by_type[item_type] = 0
                by_type[item_type] += 1
            
            return {
                'total_items': total_items,
                'completed_items': completed_items,
                'completion_rate': completed_items / max(1, total_items),
                'total_cards': total_cards,
                'reviewed_cards': reviewed_cards,
                'review_rate': reviewed_cards / max(1, total_cards),
                'by_type': by_type
            }
        except Exception as e:
            print(f"Ошибка получения общей статистики: {e}")
            return {}
    
    def export_reading_list(self, format: str = "json") -> str:
        """Экспорт списка чтения"""
        try:
            if format == "json":
                return json.dumps({i.id: asdict(i) for i in self.items.values()}, 
                                 ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Title", "Type", "Status", "Priority", "Created"])
                for item in self.items.values():
                    writer.writerow([
                        item.title,
                        item.reading_type.value,
                        item.status.value,
                        item.priority,
                        item.created_at.strftime("%Y-%m-%d")
                    ])
                return output.getvalue()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта списка чтения: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = ReadingQueueService()
    
    # Добавляем тестовый элемент
    item_id = service.add_reading_item(
        title="Статья о машинном обучении",
        url="https://example.com/ml-article",
        content="Машинное обучение - это раздел искусственного интеллекта...",
        reading_type=ReadingType.ARTICLE,
        priority=4,
        tags=["AI", "ML", "технологии"]
    )
    
    print(f"Добавлен элемент чтения: {item_id}")
    print(f"Статистика: {service.get_all_stats()}")
    print(f"Очередь чтения: {len(service.get_reading_queue())}")
