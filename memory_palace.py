# -*- coding: utf-8 -*-
"""
Memory Palace - векторная память всех разговоров и контекста
"""

import os
import json
import time
import hashlib
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import numpy as np


@dataclass
class MemoryEntry:
    """Запись в памяти"""
    id: str
    content: str
    metadata: Dict[str, Any]
    timestamp: float
    embedding: Optional[np.ndarray] = None
    importance: float = 1.0  # 0-1, важность для долгосрочной памяти
    access_count: int = 0
    last_accessed: float = 0.0
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class ConversationMemory:
    """Память о разговоре"""
    conversation_id: str
    participants: List[str]
    company: str
    role: str
    start_time: float
    end_time: Optional[float]
    summary: str
    key_points: List[str]
    sentiment_trend: str  # "positive", "negative", "neutral"
    outcome: str  # "offer", "rejection", "follow_up", "ongoing"
    salary_discussed: Optional[float] = None
    next_steps: List[str] = None

    def __post_init__(self):
        if self.next_steps is None:
            self.next_steps = []


class MemoryPalace:
    """
    Векторная память МАГА - хранит все разговоры, контекст, паттерны
    """

    def __init__(self,
                 storage_path: str = "memory_store",
                 max_memories: int = 10000,
                 embedding_dim: int = 384,  # для sentence-transformers
                 use_vector_db: bool = True):
        """
        Args:
            storage_path: Путь для хранения памяти
            max_memories: Максимальное количество воспоминаний
            embedding_dim: Размерность эмбеддингов
            use_vector_db: Использовать векторную БД
        """
        self.storage_path = storage_path
        self.max_memories = max_memories
        self.embedding_dim = embedding_dim
        self.use_vector_db = use_vector_db

        # Создаем директорию
        os.makedirs(storage_path, exist_ok=True)

        # Инициализация хранилищ
        self.memories: List[MemoryEntry] = []
        self.conversations: Dict[str, ConversationMemory] = {}
        self.vector_db = None
        self.embedding_model = None

        # Статистика
        self.stats = {
            'total_memories': 0,
            'conversations_count': 0,
            'companies_tracked': set(),
            'people_tracked': set()
        }

        # Инициализация
        self._initialize_memory_system()

    def _initialize_memory_system(self):
        """Инициализация системы памяти"""
        try:
            # Загружаем существующие данные
            self._load_memories()
            self._load_conversations()

            # Инициализируем векторную БД
            if self.use_vector_db:
                self._init_vector_db()

            # Инициализируем модель эмбеддингов
            self._init_embedding_model()

            print(f"[MemoryPalace] Инициализирован. {len(self.memories)} воспоминаний, {len(self.conversations)} разговоров")

        except Exception as e:
            print(f"[MemoryPalace] Ошибка инициализации: {e}")

    def _init_vector_db(self):
        """Инициализация векторной БД"""
        try:
            import chromadb
            from chromadb.config import Settings

            self.vector_db = chromadb.PersistentClient(
                path=os.path.join(self.storage_path, "vector_db"),
                settings=Settings(anonymized_telemetry=False)
            )

            # Создаем коллекцию для воспоминаний
            try:
                self.memories_collection = self.vector_db.get_collection("memories")
            except:
                self.memories_collection = self.vector_db.create_collection("memories")

            print("[MemoryPalace] ChromaDB инициализирован")

        except ImportError:
            print("[MemoryPalace] ChromaDB не установлен, используем in-memory")
            self.use_vector_db = False
        except Exception as e:
            print(f"[MemoryPalace] Ошибка инициализации ChromaDB: {e}")
            self.use_vector_db = False

    def _init_embedding_model(self):
        """Инициализация модели эмбеддингов"""
        try:
            from sentence_transformers import SentenceTransformer

            # Легкая модель для эмбеддингов
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            print("[MemoryPalace] SentenceTransformer инициализирован")

        except ImportError:
            print("[MemoryPalace] SentenceTransformers не установлен, эмбеддинги отключены")
            self.embedding_model = None
        except Exception as e:
            print(f"[MemoryPalace] Ошибка загрузки модели эмбеддингов: {e}")
            self.embedding_model = None

    def _load_memories(self):
        """Загрузка воспоминаний из файла"""
        try:
            memories_file = os.path.join(self.storage_path, "memories.json")
            if os.path.exists(memories_file):
                with open(memories_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for item in data:
                    # Восстанавливаем numpy array из списка
                    embedding = None
                    if item.get('embedding'):
                        embedding = np.array(item['embedding'])

                    memory = MemoryEntry(
                        id=item['id'],
                        content=item['content'],
                        metadata=item['metadata'],
                        timestamp=item['timestamp'],
                        embedding=embedding,
                        importance=item.get('importance', 1.0),
                        access_count=item.get('access_count', 0),
                        last_accessed=item.get('last_accessed', 0.0),
                        tags=item.get('tags', [])
                    )
                    self.memories.append(memory)

                self.stats['total_memories'] = len(self.memories)

        except Exception as e:
            print(f"[MemoryPalace] Ошибка загрузки воспоминаний: {e}")

    def _load_conversations(self):
        """Загрузка разговоров из файла"""
        try:
            conv_file = os.path.join(self.storage_path, "conversations.json")
            if os.path.exists(conv_file):
                with open(conv_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for conv_id, conv_data in data.items():
                    conversation = ConversationMemory(**conv_data)
                    self.conversations[conv_id] = conversation

                self.stats['conversations_count'] = len(self.conversations)

                # Обновляем статистику компаний и людей
                for conv in self.conversations.values():
                    self.stats['companies_tracked'].add(conv.company)
                    self.stats['people_tracked'].update(conv.participants)

        except Exception as e:
            print(f"[MemoryPalace] Ошибка загрузки разговоров: {e}")

    def _save_memories(self):
        """Сохранение воспоминаний"""
        try:
            memories_file = os.path.join(self.storage_path, "memories.json")

            # Конвертируем в сериализуемый формат
            data = []
            for memory in self.memories[-self.max_memories:]:  # Сохраняем только последние
                item = asdict(memory)
                if memory.embedding is not None:
                    item['embedding'] = memory.embedding.tolist()
                data.append(item)

            with open(memories_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[MemoryPalace] Ошибка сохранения воспоминаний: {e}")

    def _save_conversations(self):
        """Сохранение разговоров"""
        try:
            conv_file = os.path.join(self.storage_path, "conversations.json")

            data = {}
            for conv_id, conv in self.conversations.items():
                data[conv_id] = asdict(conv)

            with open(conv_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[MemoryPalace] Ошибка сохранения разговоров: {e}")

    def add_memory(self,
                  content: str,
                  metadata: Dict[str, Any] = None,
                  tags: List[str] = None,
                  importance: float = 1.0) -> str:
        """Добавление нового воспоминания"""
        if metadata is None:
            metadata = {}
        if tags is None:
            tags = []

        # Генерируем ID
        memory_id = hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:16]

        # Создаем эмбеддинг
        embedding = None
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode(content)
            except Exception as e:
                print(f"[MemoryPalace] Ошибка создания эмбеддинга: {e}")

        # Создаем запись
        memory = MemoryEntry(
            id=memory_id,
            content=content,
            metadata=metadata,
            timestamp=time.time(),
            embedding=embedding,
            importance=importance,
            tags=tags
        )

        self.memories.append(memory)
        self.stats['total_memories'] += 1

        # Добавляем в векторную БД
        if self.use_vector_db and embedding is not None:
            try:
                self.memories_collection.add(
                    embeddings=[embedding.tolist()],
                    metadatas=[{
                        'id': memory_id,
                        'content': content[:500],  # Ограничение для metadata
                        'tags': ','.join(tags),
                        'importance': str(importance)
                    }],
                    ids=[memory_id]
                )
            except Exception as e:
                print(f"[MemoryPalace] Ошибка добавления в векторную БД: {e}")

        # Автосохранение каждые 10 воспоминаний
        if len(self.memories) % 10 == 0:
            self._save_memories()

        return memory_id

    def search_memories(self,
                       query: str,
                       limit: int = 10,
                       tags: List[str] = None,
                       time_range: Tuple[float, float] = None) -> List[MemoryEntry]:
        """Поиск воспоминаний по запросу"""
        try:
            # Если есть векторная БД - используем семантический поиск
            if self.use_vector_db and self.embedding_model:
                return self._semantic_search(query, limit, tags, time_range)
            else:
                return self._keyword_search(query, limit, tags, time_range)

        except Exception as e:
            print(f"[MemoryPalace] Ошибка поиска: {e}")
            return []

    def _semantic_search(self,
                        query: str,
                        limit: int,
                        tags: List[str],
                        time_range: Tuple[float, float]) -> List[MemoryEntry]:
        """Семантический поиск через векторную БД"""
        try:
            # Создаем эмбеддинг запроса
            query_embedding = self.embedding_model.encode(query)

            # Формируем запрос к ChromaDB
            where_clause = {}
            if tags:
                where_clause['tags'] = {'$in': tags}

            results = self.memories_collection.query(
                query_embeddings=[query_embedding.tolist()],
                n_results=limit,
                where=where_clause if where_clause else None
            )

            # Преобразуем результаты обратно в MemoryEntry
            found_memories = []
            if results['ids']:
                for i, memory_id in enumerate(results['ids'][0]):
                    # Находим оригинальную запись
                    memory = next((m for m in self.memories if m.id == memory_id), None)
                    if memory:
                        memory.access_count += 1
                        memory.last_accessed = time.time()
                        found_memories.append(memory)

            return found_memories

        except Exception as e:
            print(f"[MemoryPalace] Ошибка семантического поиска: {e}")
            return self._keyword_search(query, limit, tags, time_range)

    def _keyword_search(self,
                       query: str,
                       limit: int,
                       tags: List[str],
                       time_range: Tuple[float, float]) -> List[MemoryEntry]:
        """Поиск по ключевым словам"""
        query_lower = query.lower()
        results = []

        for memory in self.memories:
            # Проверяем временной диапазон
            if time_range and not (time_range[0] <= memory.timestamp <= time_range[1]):
                continue

            # Проверяем теги
            if tags and not any(tag in memory.tags for tag in tags):
                continue

            # Проверяем совпадение по содержимому
            if query_lower in memory.content.lower():
                memory.access_count += 1
                memory.last_accessed = time.time()
                results.append(memory)

        # Сортируем по релевантности (важность + частота доступа)
        results.sort(key=lambda x: (x.importance, x.access_count), reverse=True)

        return results[:limit]

    def start_conversation(self,
                          participants: List[str],
                          company: str,
                          role: str) -> str:
        """Начало отслеживания разговора"""
        conv_id = f"conv_{int(time.time())}_{hash(str(participants)) % 10000}"

        conversation = ConversationMemory(
            conversation_id=conv_id,
            participants=participants,
            company=company,
            role=role,
            start_time=time.time(),
            end_time=None,
            summary="",
            key_points=[],
            sentiment_trend="neutral",
            outcome="ongoing"
        )

        self.conversations[conv_id] = conversation
        self.stats['conversations_count'] += 1
        self.stats['companies_tracked'].add(company)
        self.stats['people_tracked'].update(participants)

        return conv_id

    def update_conversation(self,
                           conv_id: str,
                           message: str,
                           sentiment: str = "neutral"):
        """Обновление разговора новым сообщением"""
        if conv_id not in self.conversations:
            return

        conversation = self.conversations[conv_id]

        # Добавляем сообщение в память
        self.add_memory(
            content=message,
            metadata={
                'conversation_id': conv_id,
                'company': conversation.company,
                'participants': conversation.participants,
                'sentiment': sentiment
            },
            tags=['conversation', conversation.company, sentiment]
        )

        # Обновляем статистику разговора
        # Анализируем ключевые моменты
        self._analyze_conversation_message(conversation, message, sentiment)

    def _analyze_conversation_message(self,
                                    conversation: ConversationMemory,
                                    message: str,
                                    sentiment: str):
        """Анализ сообщения в разговоре"""
        message_lower = message.lower()

        # Ищем упоминания зарплаты
        import re
        salary_matches = re.findall(r'\$?(\d{1,3}(?:,\d{3})*(?:k|000)?)', message)
        if salary_matches:
            for match in salary_matches:
                salary = float(match.replace(',', '').replace('k', '000'))
                if 30000 <= salary <= 1000000:  # Реалистичный диапазон
                    conversation.salary_discussed = salary
                    break

        # Определяем исход разговора
        if any(word in message_lower for word in ['offer', 'предложение', 'оффер']):
            conversation.outcome = "offer"
        elif any(word in message_lower for word in ['reject', 'отказ', 'не подходим']):
            conversation.outcome = "rejection"
        elif any(word in message_lower for word in ['follow up', 'следующий этап', 'тестовое']):
            conversation.outcome = "follow_up"

        # Ключевые моменты
        key_indicators = [
            'experience', 'skills', 'requirements', 'deadline',
            'benefits', 'equity', 'remote', 'location',
            'опыт', 'навыки', 'требования', 'сроки'
        ]

        for indicator in key_indicators:
            if indicator in message_lower and indicator not in conversation.key_points:
                conversation.key_points.append(indicator)

    def end_conversation(self, conv_id: str, summary: str = ""):
        """Завершение разговора"""
        if conv_id not in self.conversations:
            return

        conversation = self.conversations[conv_id]
        conversation.end_time = time.time()

        if summary:
            conversation.summary = summary
        else:
            # Генерируем автоматическое summary
            conversation.summary = self._generate_conversation_summary(conversation)

        # Сохраняем
        self._save_conversations()

    def _generate_conversation_summary(self, conversation: ConversationMemory) -> str:
        """Генерация summary разговора"""
        summary_parts = []

        summary_parts.append(f"Разговор с {conversation.company} по позиции {conversation.role}")

        if conversation.participants:
            summary_parts.append(f"Участники: {', '.join(conversation.participants)}")

        if conversation.salary_discussed:
            summary_parts.append(f"Обсуждалась зарплата: ${conversation.salary_discussed:,.0f}")

        if conversation.key_points:
            summary_parts.append(f"Ключевые темы: {', '.join(conversation.key_points[:5])}")

        summary_parts.append(f"Исход: {conversation.outcome}")

        return ". ".join(summary_parts)

    def get_person_insights(self, person_name: str) -> Dict[str, Any]:
        """Получение инсайтов о человеке"""
        person_memories = [m for m in self.memories
                          if person_name in m.metadata.get('participants', [])]

        if not person_memories:
            return {}

        insights = {
            'conversations_count': len(set(m.metadata.get('conversation_id') for m in person_memories)),
            'companies': list(set(m.metadata.get('company') for m in person_memories if m.metadata.get('company'))),
            'common_topics': self._extract_common_topics(person_memories),
            'sentiment_history': [m.metadata.get('sentiment', 'neutral') for m in person_memories[-10:]],
            'last_interaction': max(m.timestamp for m in person_memories)
        }

        return insights

    def get_company_insights(self, company_name: str) -> Dict[str, Any]:
        """Получение инсайтов о компании"""
        company_conversations = [c for c in self.conversations.values() if c.company == company_name]
        company_memories = [m for m in self.memories if m.metadata.get('company') == company_name]

        if not company_conversations and not company_memories:
            return {}

        insights = {
            'conversations_count': len(company_conversations),
            'roles_discussed': list(set(c.role for c in company_conversations)),
            'salary_range': self._extract_salary_range(company_conversations),
            'common_requirements': self._extract_common_requirements(company_memories),
            'sentiment_trend': self._calculate_sentiment_trend(company_memories),
            'last_interaction': max((c.start_time for c in company_conversations), default=0)
        }

        return insights

    def _extract_common_topics(self, memories: List[MemoryEntry]) -> List[str]:
        """Извлечение общих тем"""
        all_tags = []
        for memory in memories:
            all_tags.extend(memory.tags)

        # Подсчитываем частоту
        from collections import Counter
        tag_counts = Counter(all_tags)

        return [tag for tag, count in tag_counts.most_common(10) if count > 1]

    def _extract_salary_range(self, conversations: List[ConversationMemory]) -> Tuple[Optional[float], Optional[float]]:
        """Извлечение диапазона зарплат"""
        salaries = [c.salary_discussed for c in conversations if c.salary_discussed]
        if not salaries:
            return None, None

        return min(salaries), max(salaries)

    def _extract_common_requirements(self, memories: List[MemoryEntry]) -> List[str]:
        """Извлечение общих требований"""
        requirements = []
        for memory in memories:
            content_lower = memory.content.lower()
            if 'require' in content_lower or 'треб' in content_lower:
                # Простая эвристика - извлекаем слова после ключевых
                words = memory.content.split()
                req_start = False
                for word in words:
                    if 'require' in word.lower() or 'треб' in word.lower():
                        req_start = True
                        continue
                    if req_start and len(word) > 3:
                        requirements.append(word.lower())
                        if len(requirements) >= 5:  # Ограничиваем
                            break

        return list(set(requirements))

    def _calculate_sentiment_trend(self, memories: List[MemoryEntry]) -> str:
        """Расчет тренда настроения"""
        sentiments = [m.metadata.get('sentiment', 'neutral') for m in memories[-20:]]  # Последние 20

        if not sentiments:
            return "unknown"

        positive = sentiments.count('positive')
        negative = sentiments.count('negative')
        neutral = sentiments.count('neutral')

        if positive > negative and positive > neutral:
            return "positive"
        elif negative > positive and negative > neutral:
            return "negative"
        else:
            return "neutral"

    def get_memory_stats(self) -> Dict[str, Any]:
        """Получение статистики памяти"""
        stats = dict(self.stats)
        stats['companies_tracked'] = len(stats['companies_tracked'])
        stats['people_tracked'] = len(stats['people_tracked'])

        # Дополнительная статистика
        if self.memories:
            stats['oldest_memory'] = min(m.timestamp for m in self.memories)
            stats['newest_memory'] = max(m.timestamp for m in self.memories)
            stats['avg_importance'] = sum(m.importance for m in self.memories) / len(self.memories)

        return stats

    def cleanup_old_memories(self, days_old: int = 365):
        """Очистка старых воспоминаний"""
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)

        # Оставляем только важные или недавно использованные
        self.memories = [
            m for m in self.memories
            if m.importance > 0.7 or m.last_accessed > cutoff_time or m.timestamp > cutoff_time
        ]

        self._save_memories()
        print(f"[MemoryPalace] Очищено старых воспоминаний. Осталось: {len(self.memories)}")

    def export_memory(self, filename: str):
        """Экспорт всей памяти"""
        try:
            export_data = {
                'memories': [asdict(m) for m in self.memories],
                'conversations': {k: asdict(v) for k, v in self.conversations.items()},
                'stats': self.get_memory_stats(),
                'export_time': time.time()
            }

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            print(f"[MemoryPalace] Память экспортирована в {filename}")

        except Exception as e:
            print(f"[MemoryPalace] Ошибка экспорта: {e}")

    def import_memory(self, filename: str):
        """Импорт памяти"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Импортируем воспоминания
            for item in data.get('memories', []):
                embedding = np.array(item['embedding']) if item.get('embedding') else None
                memory = MemoryEntry(**item, embedding=embedding)
                self.memories.append(memory)

            # Импортируем разговоры
            for conv_id, conv_data in data.get('conversations', {}).items():
                conversation = ConversationMemory(**conv_data)
                self.conversations[conv_id] = conversation

            self._save_memories()
            self._save_conversations()

            print(f"[MemoryPalace] Импортировано {len(data.get('memories', []))} воспоминаний")

        except Exception as e:
            print(f"[MemoryPalace] Ошибка импорта: {e}")
