# -*- coding: utf-8 -*-
"""
RAG (Retrieval-Augmented Generation) индекс для AI МАГИСТРА
Локальный поиск по резюме, проектам, кейсам
"""

import os
import json
import pickle
from datetime import datetime
from typing import List, Dict, Tuple, Optional
import numpy as np
from dataclasses import dataclass
import re


@dataclass
class Document:
    """Документ в RAG индексе"""
    id: str
    title: str
    content: str
    doc_type: str  # "resume", "project", "case_study", "achievement"
    metadata: Dict
    embedding: Optional[np.ndarray] = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class SimpleEmbedder:
    """
    Простой эмбеддер на основе TF-IDF
    (В будущем можно заменить на sentence-transformers)
    """
    
    def __init__(self):
        self.vocab = {}
        self.idf = {}
        self.doc_count = 0
        
    def fit(self, documents: List[Document]):
        """
        Обучение на документах
        """
        self.doc_count = len(documents)
        
        # Сбор всех слов
        all_words = set()
        for doc in documents:
            words = self._tokenize(doc.content)
            all_words.update(words)
        
        # Создание словаря
        self.vocab = {word: idx for idx, word in enumerate(sorted(all_words))}
        
        # Вычисление IDF
        for word in self.vocab:
            doc_freq = sum(1 for doc in documents if word in self._tokenize(doc.content))
            self.idf[word] = np.log(self.doc_count / (doc_freq + 1))
    
    def _tokenize(self, text: str) -> List[str]:
        """
        Токенизация текста
        """
        # Простая токенизация
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        return [word for word in text.split() if len(word) > 2]
    
    def _compute_tf(self, text: str) -> Dict[str, float]:
        """
        Вычисление TF для текста
        """
        words = self._tokenize(text)
        word_count = {}
        for word in words:
            word_count[word] = word_count.get(word, 0) + 1
        
        total_words = len(words)
        tf = {word: count / total_words for word, count in word_count.items()}
        return tf
    
    def embed(self, text: str) -> np.ndarray:
        """
        Создание эмбеддинга для текста
        """
        tf = self._compute_tf(text)
        embedding = np.zeros(len(self.vocab))
        
        for word, tf_score in tf.items():
            if word in self.vocab:
                word_idx = self.vocab[word]
                idf_score = self.idf.get(word, 0)
                embedding[word_idx] = tf_score * idf_score
        
        # Нормализация
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding


class RAGIndex:
    """
    RAG индекс для поиска по документам
    """
    
    def __init__(self, index_dir: str = "data/rag_index"):
        self.index_dir = index_dir
        self.documents: List[Document] = []
        self.embedder = SimpleEmbedder()
        self.is_trained = False
        
        # Создание директории
        os.makedirs(index_dir, exist_ok=True)
        
    def add_document(self, title: str, content: str, doc_type: str, metadata: Dict = None) -> str:
        """
        Добавление документа в индекс
        """
        doc_id = f"{doc_type}_{int(datetime.now().timestamp())}"
        
        document = Document(
            id=doc_id,
            title=title,
            content=content,
            doc_type=doc_type,
            metadata=metadata or {}
        )
        
        self.documents.append(document)
        print(f"📄 Добавлен документ: {title}")
        
        return doc_id
    
    def add_resume_section(self, section: str, content: str, metadata: Dict = None):
        """
        Добавление раздела резюме
        """
        return self.add_document(
            title=f"Резюме: {section}",
            content=content,
            doc_type="resume",
            metadata=metadata
        )
    
    def add_project(self, name: str, description: str, tech_stack: List[str], 
                   achievements: List[str], metadata: Dict = None):
        """
        Добавление проекта
        """
        content = f"""
        Проект: {name}
        
        Описание: {description}
        
        Технологии: {', '.join(tech_stack)}
        
        Достижения:
        {chr(10).join(f"- {achievement}" for achievement in achievements)}
        """
        
        return self.add_document(
            title=f"Проект: {name}",
            content=content,
            doc_type="project",
            metadata={
                "tech_stack": tech_stack,
                "achievements": achievements,
                **(metadata or {})
            }
        )
    
    def add_achievement(self, title: str, description: str, metrics: Dict, metadata: Dict = None):
        """
        Добавление достижения
        """
        content = f"""
        Достижение: {title}
        
        Описание: {description}
        
        Метрики:
        {chr(10).join(f"- {key}: {value}" for key, value in metrics.items())}
        """
        
        return self.add_document(
            title=f"Достижение: {title}",
            content=content,
            doc_type="achievement",
            metadata={
                "metrics": metrics,
                **(metadata or {})
            }
        )
    
    def train_index(self):
        """
        Обучение индекса
        """
        if not self.documents:
            print("❌ Нет документов для обучения")
            return False
        
        print(f"🧠 Обучение RAG индекса на {len(self.documents)} документах...")
        
        # Обучение эмбеддера
        self.embedder.fit(self.documents)
        
        # Создание эмбеддингов для всех документов
        for doc in self.documents:
            doc.embedding = self.embedder.embed(doc.content)
        
        self.is_trained = True
        print("✅ RAG индекс обучен")
        
        return True
    
    def search(self, query: str, top_k: int = 5, doc_types: List[str] = None) -> List[Tuple[Document, float]]:
        """
        Поиск по индексу
        """
        if not self.is_trained:
            print("❌ Индекс не обучен")
            return []
        
        # Создание эмбеддинга запроса
        query_embedding = self.embedder.embed(query)
        
        # Вычисление схожести
        similarities = []
        for doc in self.documents:
            if doc_types and doc.doc_type not in doc_types:
                continue
                
            if doc.embedding is not None:
                similarity = np.dot(query_embedding, doc.embedding)
                similarities.append((doc, similarity))
        
        # Сортировка по схожести
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def get_context_for_query(self, query: str, max_context_length: int = 1000) -> str:
        """
        Получение контекста для запроса
        """
        results = self.search(query, top_k=3)
        
        if not results:
            return "Контекст не найден"
        
        context_parts = []
        current_length = 0
        
        for doc, similarity in results:
            if current_length >= max_context_length:
                break
                
            context_part = f"[{doc.doc_type.upper()}] {doc.title}\n{doc.content[:200]}...\n"
            
            if current_length + len(context_part) <= max_context_length:
                context_parts.append(context_part)
                current_length += len(context_part)
        
        return "\n".join(context_parts)
    
    def save_index(self, filename: str = None):
        """
        Сохранение индекса
        """
        if filename is None:
            filename = os.path.join(self.index_dir, f"rag_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl")
        
        index_data = {
            "documents": self.documents,
            "embedder_vocab": self.embedder.vocab,
            "embedder_idf": self.embedder.idf,
            "embedder_doc_count": self.embedder.doc_count,
            "is_trained": self.is_trained,
            "created_at": datetime.now().isoformat()
        }
        
        with open(filename, 'wb') as f:
            pickle.dump(index_data, f)
        
        print(f"💾 Индекс сохранен: {filename}")
        return filename
    
    def load_index(self, filename: str):
        """
        Загрузка индекса
        """
        try:
            with open(filename, 'rb') as f:
                index_data = pickle.load(f)
            
            self.documents = index_data["documents"]
            self.embedder.vocab = index_data["embedder_vocab"]
            self.embedder.idf = index_data["embedder_idf"]
            self.embedder.doc_count = index_data["embedder_doc_count"]
            self.is_trained = index_data["is_trained"]
            
            print(f"📂 Индекс загружен: {filename}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка загрузки индекса: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """
        Статистика индекса
        """
        if not self.documents:
            return {"message": "Индекс пуст"}
        
        doc_types = {}
        for doc in self.documents:
            doc_types[doc.doc_type] = doc_types.get(doc.doc_type, 0) + 1
        
        return {
            "total_documents": len(self.documents),
            "document_types": doc_types,
            "is_trained": self.is_trained,
            "vocabulary_size": len(self.embedder.vocab) if self.embedder.vocab else 0
        }


class RAGManager:
    """
    Менеджер RAG индекса
    """
    
    def __init__(self, index_dir: str = "data/rag_index"):
        self.index = RAGIndex(index_dir)
        self.is_initialized = False
        
    def initialize(self) -> bool:
        """
        Инициализация RAG менеджера
        """
        try:
            # Попытка загрузки существующего индекса
            index_files = [f for f in os.listdir(self.index.index_dir) if f.endswith('.pkl')]
            if index_files:
                latest_index = max(index_files)
                self.index.load_index(os.path.join(self.index.index_dir, latest_index))
                print("📂 Загружен существующий RAG индекс")
            else:
                # Создание нового индекса с базовыми данными
                self._create_default_index()
                print("🆕 Создан новый RAG индекс")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            print(f"❌ Ошибка инициализации RAG: {e}")
            return False
    
    def _create_default_index(self):
        """
        Создание индекса с базовыми данными AI МАГИСТРА
        """
        # Резюме
        self.index.add_resume_section(
            "Опыт работы",
            """
            Senior ML Engineer с 5+ лет опыта в production ML системах.
            Специализация: LLM, агентные системы, оптимизация инференса.
            Последняя позиция: Tech Lead в AI стартапе.
            """
        )
        
        self.index.add_resume_section(
            "Навыки",
            """
            Python, PyTorch, TensorFlow, FastAPI, Docker, Kubernetes.
            ML Ops: MLflow, Weights & Biases, Prometheus.
            Cloud: AWS, GCP, Azure.
            """
        )
        
        # Проекты
        self.index.add_project(
            "Prometheus LLM",
            "Production LLM система с оптимизированным инференсом",
            ["Python", "PyTorch", "FastAPI", "Docker"],
            [
                "p95 латентность 1.2s",
                "Пропускная способность 45-60 токенов/сек",
                "Низкая себестоимость на 1000 токенов"
            ]
        )
        
        self.index.add_project(
            "AI Agent Framework",
            "Фреймворк для создания агентных систем",
            ["Python", "LangChain", "OpenAI API", "PostgreSQL"],
            [
                "Поддержка 10+ типов агентов",
                "Автоматическое планирование задач",
                "Интеграция с внешними API"
            ]
        )
        
        # Достижения
        self.index.add_achievement(
            "Оптимизация инференса",
            "Снижение латентности LLM в 3 раза",
            {
                "latency_improvement": "3x",
                "cost_reduction": "40%",
                "throughput_increase": "2.5x"
            }
        )
        
        # Обучение индекса
        self.index.train_index()
    
    def search_context(self, query: str, max_length: int = 1000) -> str:
        """
        Поиск контекста для запроса
        """
        if not self.is_initialized:
            return "RAG не инициализирован"
        
        return self.index.get_context_for_query(query, max_length)
    
    def add_personal_document(self, title: str, content: str, doc_type: str):
        """
        Добавление личного документа
        """
        if not self.is_initialized:
            return False
        
        doc_id = self.index.add_document(title, content, doc_type)
        self.index.train_index()  # Переобучение после добавления
        return doc_id


# =============== ТЕСТИРОВАНИЕ ===============

def test_rag_index():
    """
    Тестирование RAG индекса
    """
    print("🧪 Тестирование RAG индекса...")
    
    # Создание менеджера
    rag_manager = RAGManager()
    
    # Инициализация
    if rag_manager.initialize():
        print("✅ RAG менеджер инициализирован")
        
        # Тестовые запросы
        test_queries = [
            "Какие у меня навыки в Python?",
            "Расскажи о проекте Prometheus",
            "Какие у меня достижения в оптимизации?",
            "Какой у меня опыт с ML?"
        ]
        
        for query in test_queries:
            print(f"\n🔍 Запрос: {query}")
            context = rag_manager.search_context(query)
            print(f"📄 Контекст: {context[:200]}...")
        
        # Статистика
        stats = rag_manager.index.get_stats()
        print(f"\n📊 Статистика: {stats}")
        
    else:
        print("❌ Ошибка инициализации RAG")


if __name__ == "__main__":
    test_rag_index()
