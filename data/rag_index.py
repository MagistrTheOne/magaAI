# -*- coding: utf-8 -*-
"""
RAG (Retrieval-Augmented Generation) система для AIMagistr 3.0
Импорт, индексация и поиск по документам
"""

import os
import json
import asyncio
import logging
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from pathlib import Path
import time

try:
    import numpy as np
    from sentence_transformers import SentenceTransformer
    import faiss
    import PyPDF2
    import docx
    import markdown
    import requests
    from bs4 import BeautifulSoup
    RAG_DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: RAG зависимости недоступны: {e}")
    RAG_DEPENDENCIES_AVAILABLE = False
    # Создаем заглушки для тестирования
    class np:
        @staticmethod
        def array(data):
            return data
        @staticmethod
        def normalize_L2(data):
            return data
    class SentenceTransformer:
        def __init__(self, *args, **kwargs):
            pass
        def encode(self, texts):
            return [[0.1] * 384 for _ in texts]
        def get_sentence_embedding_dimension(self):
            return 384
    class faiss:
        class IndexFlatIP:
            def __init__(self, dim):
                self.dim = dim
                self.ntotal = 0
            def add(self, data):
                self.ntotal += len(data)
            def search(self, query, k):
                return [[0.1] * k], [[0] * k]
        @staticmethod
        def normalize_L2(data):
            return data
        @staticmethod
        def write_index(index, path):
            pass
        @staticmethod
        def read_index(path):
            return faiss.IndexFlatIP(384)


class RAGIndex:
    """
    RAG система для индексации и поиска по документам
    """
    
    def __init__(self, index_dir: str = "data/rag_index"):
        self.logger = logging.getLogger("RAGIndex")
        
        # Конфигурация
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Модель эмбеддингов
        self.embedding_model = None
        self.embedding_dim = 384  # Размерность эмбеддингов
        
        # FAISS индекс
        self.faiss_index = None
        self.document_metadata = []
        self.document_chunks = []
        
        # Настройки
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.max_documents = 10000
        
        # Инициализация
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов"""
        try:
            if not RAG_DEPENDENCIES_AVAILABLE:
                self.logger.warning("RAG зависимости недоступны")
                return
            
            # Загружаем модель эмбеддингов
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            
            # Инициализируем FAISS индекс
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            
            # Загружаем существующий индекс
            self._load_index()
            
            self.logger.info("RAG система инициализирована")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации RAG: {e}")
    
    def _load_index(self):
        """Загрузка существующего индекса"""
        try:
            index_file = self.index_dir / "faiss_index.bin"
            metadata_file = self.index_dir / "metadata.json"
            
            if index_file.exists() and metadata_file.exists():
                # Загружаем FAISS индекс
                self.faiss_index = faiss.read_index(str(index_file))
                
                # Загружаем метаданные
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.document_metadata = data.get('metadata', [])
                    self.document_chunks = data.get('chunks', [])
                
                self.logger.info(f"Загружен индекс с {len(self.document_metadata)} документами")
            
        except Exception as e:
            self.logger.error(f"Ошибка загрузки индекса: {e}")
    
    def _save_index(self):
        """Сохранение индекса"""
        try:
            # Сохраняем FAISS индекс
            index_file = self.index_dir / "faiss_index.bin"
            faiss.write_index(self.faiss_index, str(index_file))
            
            # Сохраняем метаданные
            metadata_file = self.index_dir / "metadata.json"
            data = {
                'metadata': self.document_metadata,
                'chunks': self.document_chunks,
                'timestamp': time.time()
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info("Индекс сохранен")
            
        except Exception as e:
            self.logger.error(f"Ошибка сохранения индекса: {e}")
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Извлечение текста из PDF"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из PDF: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Извлечение текста из DOCX"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из DOCX: {e}")
            return ""
    
    def _extract_text_from_markdown(self, file_path: str) -> str:
        """Извлечение текста из Markdown"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                md_content = file.read()
                html = markdown.markdown(md_content)
                soup = BeautifulSoup(html, 'html.parser')
                return soup.get_text()
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста из Markdown: {e}")
            return ""
    
    def _extract_text_from_url(self, url: str) -> str:
        """Извлечение текста с веб-страницы"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Удаляем скрипты и стили
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Извлекаем текст
            text = soup.get_text()
            
            # Очищаем текст
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
        except Exception as e:
            self.logger.error(f"Ошибка извлечения текста с URL: {e}")
            return ""
    
    def _chunk_text(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """Разбивка текста на чанки"""
        if chunk_size is None:
            chunk_size = self.chunk_size
        if overlap is None:
            overlap = self.chunk_overlap
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _generate_embeddings(self, texts: List[str]):
        """Генерация эмбеддингов для текстов"""
        try:
            if not self.embedding_model:
                raise ValueError("Модель эмбеддингов не инициализирована")
            
            embeddings = self.embedding_model.encode(texts)
            return embeddings
        except Exception as e:
            self.logger.error(f"Ошибка генерации эмбеддингов: {e}")
            return []
    
    async def add_document(self, file_path: str, metadata: Dict[str, Any] = None) -> bool:
        """Добавление документа в индекс"""
        try:
            if not RAG_DEPENDENCIES_AVAILABLE:
                return False
            
            # Проверяем лимит документов
            if len(self.document_metadata) >= self.max_documents:
                self.logger.warning("Достигнут лимит документов")
                return False
            
            # Определяем тип файла
            file_ext = Path(file_path).suffix.lower()
            
            # Извлекаем текст
            text = ""
            if file_ext == '.pdf':
                text = self._extract_text_from_pdf(file_path)
            elif file_ext == '.docx':
                text = self._extract_text_from_docx(file_path)
            elif file_ext in ['.md', '.markdown']:
                text = self._extract_text_from_markdown(file_path)
            elif file_ext in ['.txt', '.text']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
            else:
                self.logger.warning(f"Неподдерживаемый формат файла: {file_ext}")
                return False
            
            if not text.strip():
                self.logger.warning("Документ не содержит текста")
                return False
            
            # Разбиваем на чанки
            chunks = self._chunk_text(text)
            
            if not chunks:
                self.logger.warning("Не удалось разбить документ на чанки")
                return False
            
            # Генерируем эмбеддинги
            embeddings = self._generate_embeddings(chunks)
            
            if embeddings.size == 0:
                self.logger.warning("Не удалось сгенерировать эмбеддинги")
                return False
            
            # Нормализуем эмбеддинги для FAISS
            faiss.normalize_L2(embeddings)
            
            # Добавляем в индекс
            self.faiss_index.add(embeddings)
            
            # Сохраняем метаданные
            doc_id = hashlib.md5(file_path.encode()).hexdigest()
            doc_metadata = {
                'id': doc_id,
                'file_path': file_path,
                'title': metadata.get('title', Path(file_path).name),
                'type': metadata.get('type', 'document'),
                'language': metadata.get('language', 'ru'),
                'created_at': datetime.now().isoformat(),
                'chunk_count': len(chunks),
                'text_length': len(text)
            }
            
            self.document_metadata.append(doc_metadata)
            
            # Сохраняем чанки
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    'doc_id': doc_id,
                    'chunk_index': i,
                    'text': chunk,
                    'start_index': i * (self.chunk_size - self.chunk_overlap)
                }
                self.document_chunks.append(chunk_metadata)
            
            # Сохраняем индекс
            self._save_index()
            
            self.logger.info(f"Документ добавлен: {file_path} ({len(chunks)} чанков)")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления документа: {e}")
            return False
    
    async def add_url(self, url: str, metadata: Dict[str, Any] = None) -> bool:
        """Добавление веб-страницы в индекс"""
        try:
            if not RAG_DEPENDENCIES_AVAILABLE:
                return False
            
            # Извлекаем текст с URL
            text = self._extract_text_from_url(url)
            
            if not text.strip():
                self.logger.warning("URL не содержит текста")
                return False
            
            # Создаем временный файл
            temp_file = self.index_dir / f"temp_{hashlib.md5(url.encode()).hexdigest()}.txt"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(text)
            
            # Добавляем как документ
            result = await self.add_document(str(temp_file), metadata)
            
            # Удаляем временный файл
            if temp_file.exists():
                temp_file.unlink()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления URL: {e}")
            return False
    
    async def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Поиск по индексу"""
        try:
            if not RAG_DEPENDENCIES_AVAILABLE or not self.embedding_model:
                return []
            
            if self.faiss_index.ntotal == 0:
                return []
            
            # Генерируем эмбеддинг для запроса
            query_embedding = self.embedding_model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Поиск в FAISS
            scores, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Формируем результаты
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.document_chunks):
                    chunk = self.document_chunks[idx]
                    
                    # Находим метаданные документа
                    doc_metadata = None
                    for doc in self.document_metadata:
                        if doc['id'] == chunk['doc_id']:
                            doc_metadata = doc
                            break
                    
                    results.append({
                        'chunk': chunk,
                        'document': doc_metadata,
                        'score': float(score),
                        'text': chunk['text']
                    })
            
            return results
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска: {e}")
            return []
    
    async def get_document_chunks(self, doc_id: str) -> List[Dict[str, Any]]:
        """Получение всех чанков документа"""
        try:
            chunks = [chunk for chunk in self.document_chunks if chunk['doc_id'] == doc_id]
            return chunks
        except Exception as e:
            self.logger.error(f"Ошибка получения чанков документа: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики индекса"""
        return {
            'total_documents': len(self.document_metadata),
            'total_chunks': len(self.document_chunks),
            'index_size': self.faiss_index.ntotal if self.faiss_index else 0,
            'embedding_dimension': self.embedding_dim,
            'chunk_size': self.chunk_size,
            'chunk_overlap': self.chunk_overlap,
            'max_documents': self.max_documents
        }
    
    def get_documents(self) -> List[Dict[str, Any]]:
        """Получение списка всех документов"""
        return self.document_metadata.copy()
    
    async def remove_document(self, doc_id: str) -> bool:
        """Удаление документа из индекса"""
        try:
            # Находим документ
            doc_index = None
            for i, doc in enumerate(self.document_metadata):
                if doc['id'] == doc_id:
                    doc_index = i
                    break
            
            if doc_index is None:
                return False
            
            # Удаляем чанки
            chunk_indices = []
            for i, chunk in enumerate(self.document_chunks):
                if chunk['doc_id'] == doc_id:
                    chunk_indices.append(i)
            
            # Удаляем в обратном порядке
            for i in reversed(chunk_indices):
                del self.document_chunks[i]
            
            # Удаляем метаданные
            del self.document_metadata[doc_index]
            
            # Пересоздаем индекс
            if self.document_chunks:
                # Генерируем эмбеддинги для всех чанков
                texts = [chunk['text'] for chunk in self.document_chunks]
                embeddings = self._generate_embeddings(texts)
                faiss.normalize_L2(embeddings)
                
                # Создаем новый индекс
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
                self.faiss_index.add(embeddings)
            else:
                # Создаем пустой индекс
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            
            # Сохраняем индекс
            self._save_index()
            
            self.logger.info(f"Документ удален: {doc_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка удаления документа: {e}")
            return False
    
    async def clear_index(self):
        """Очистка всего индекса"""
        try:
            self.document_metadata.clear()
            self.document_chunks.clear()
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dim)
            self._save_index()
            self.logger.info("Индекс очищен")
        except Exception as e:
            self.logger.error(f"Ошибка очистки индекса: {e}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Проверка здоровья RAG системы"""
        try:
            if not RAG_DEPENDENCIES_AVAILABLE:
                return {
                    "status": "error",
                    "message": "RAG зависимости недоступны"
                }
            
            if not self.embedding_model:
                return {
                    "status": "error",
                    "message": "Модель эмбеддингов не инициализирована"
                }
            
            stats = self.get_stats()
            
            return {
                "status": "healthy",
                "message": "RAG система работает",
                "stats": stats
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)}"
            }


# Функция для тестирования
async def test_rag_system():
    """Тестирование RAG системы"""
    rag = RAGIndex()
    
    print("Testing RAG System...")
    
    # Статистика
    stats = rag.get_stats()
    print(f"Stats: {stats}")
    
    # Health check
    health = await rag.health_check()
    print(f"Health: {health}")
    
    # Тестовый поиск
    if stats['total_chunks'] > 0:
        results = await rag.search("тест", top_k=3)
        print(f"Search results: {len(results)}")
        for result in results:
            print(f"  Score: {result['score']:.3f}, Text: {result['text'][:100]}...")


if __name__ == "__main__":
    asyncio.run(test_rag_system())
