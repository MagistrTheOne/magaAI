# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Автокаталог документов по содержимому/тегам
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid
import hashlib

class DocumentType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    EMAIL = "email"
    OTHER = "other"

class DocumentCategory(Enum):
    WORK = "work"
    PERSONAL = "personal"
    FINANCIAL = "financial"
    LEGAL = "legal"
    MEDICAL = "medical"
    EDUCATIONAL = "educational"
    TRAVEL = "travel"
    OTHER = "other"

@dataclass
class Document:
    id: str
    filename: str
    file_path: str
    file_size: int
    document_type: DocumentType
    category: DocumentCategory
    title: str
    description: str
    content_preview: str
    tags: List[str]
    created_at: datetime
    modified_at: datetime
    file_hash: str
    metadata: Dict[str, Any] = None
    auto_generated: bool = True
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class DocumentTag:
    id: str
    name: str
    description: str
    color: str
    created_at: datetime
    usage_count: int = 0

class DocAutocatalogService:
    """Сервис автокаталога документов"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.documents_file = self.storage_dir / "documents.json"
        self.tags_file = self.storage_dir / "document_tags.json"
        
        # Загружаем данные
        self.documents = self._load_documents()
        self.tags = self._load_tags()
    
    def _load_documents(self) -> Dict[str, Document]:
        """Загрузка документов из файла"""
        try:
            if self.documents_file.exists():
                with open(self.documents_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    documents = {}
                    for doc_id, doc_data in data.items():
                        doc_data['document_type'] = DocumentType(doc_data['document_type'])
                        doc_data['category'] = DocumentCategory(doc_data['category'])
                        doc_data['created_at'] = datetime.fromisoformat(doc_data['created_at'])
                        doc_data['modified_at'] = datetime.fromisoformat(doc_data['modified_at'])
                        documents[doc_id] = Document(**doc_data)
                    return documents
        except Exception as e:
            print(f"Ошибка загрузки документов: {e}")
        return {}
    
    def _save_documents(self):
        """Сохранение документов в файл"""
        try:
            data = {}
            for doc_id, document in self.documents.items():
                doc_dict = asdict(document)
                doc_dict['document_type'] = document.document_type.value
                doc_dict['category'] = document.category.value
                doc_dict['created_at'] = document.created_at.isoformat()
                doc_dict['modified_at'] = document.modified_at.isoformat()
                data[doc_id] = doc_dict
            
            with open(self.documents_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения документов: {e}")
    
    def _load_tags(self) -> Dict[str, DocumentTag]:
        """Загрузка тегов из файла"""
        try:
            if self.tags_file.exists():
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tags = {}
                    for tag_id, tag_data in data.items():
                        tag_data['created_at'] = datetime.fromisoformat(tag_data['created_at'])
                        tags[tag_id] = DocumentTag(**tag_data)
                    return tags
        except Exception as e:
            print(f"Ошибка загрузки тегов: {e}")
        return {}
    
    def _save_tags(self):
        """Сохранение тегов в файл"""
        try:
            data = {}
            for tag_id, tag in self.tags.items():
                tag_dict = asdict(tag)
                tag_dict['created_at'] = tag.created_at.isoformat()
                data[tag_id] = tag_dict
            
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения тегов: {e}")
    
    def _detect_document_type(self, filename: str, content: str = "") -> DocumentType:
        """Определение типа документа"""
        try:
            extension = Path(filename).suffix.lower()
            
            if extension in ['.pdf']:
                return DocumentType.PDF
            elif extension in ['.docx', '.doc']:
                return DocumentType.DOCX
            elif extension in ['.txt', '.md']:
                return DocumentType.TXT
            elif extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                return DocumentType.IMAGE
            elif extension in ['.xlsx', '.xls', '.csv']:
                return DocumentType.SPREADSHEET
            elif extension in ['.pptx', '.ppt']:
                return DocumentType.PRESENTATION
            elif extension in ['.eml', '.msg']:
                return DocumentType.EMAIL
            else:
                return DocumentType.OTHER
        except Exception as e:
            print(f"Ошибка определения типа документа: {e}")
            return DocumentType.OTHER
    
    def _categorize_document(self, content: str, filename: str) -> DocumentCategory:
        """Автоматическая категоризация документа"""
        try:
            content_lower = content.lower()
            filename_lower = filename.lower()
            
            # Паттерны для категоризации
            patterns = {
                DocumentCategory.WORK: [
                    'отчет', 'report', 'презентация', 'presentation', 'проект', 'project',
                    'задача', 'task', 'встреча', 'meeting', 'контракт', 'contract'
                ],
                DocumentCategory.FINANCIAL: [
                    'чек', 'receipt', 'счет', 'invoice', 'платеж', 'payment', 'банк', 'bank',
                    'кредит', 'credit', 'депозит', 'deposit', 'налог', 'tax'
                ],
                DocumentCategory.LEGAL: [
                    'договор', 'agreement', 'соглашение', 'contract', 'право', 'law',
                    'суд', 'court', 'юрист', 'lawyer', 'закон', 'legal'
                ],
                DocumentCategory.MEDICAL: [
                    'медицинский', 'medical', 'врач', 'doctor', 'лечение', 'treatment',
                    'анализ', 'analysis', 'диагноз', 'diagnosis', 'рецепт', 'prescription'
                ],
                DocumentCategory.EDUCATIONAL: [
                    'учеба', 'study', 'курс', 'course', 'лекция', 'lecture', 'экзамен', 'exam',
                    'диплом', 'diploma', 'сертификат', 'certificate'
                ],
                DocumentCategory.TRAVEL: [
                    'путешествие', 'travel', 'билет', 'ticket', 'отель', 'hotel',
                    'виза', 'visa', 'паспорт', 'passport', 'рейс', 'flight'
                ]
            }
            
            # Подсчитываем совпадения
            category_scores = {}
            for category, keywords in patterns.items():
                score = 0
                for keyword in keywords:
                    if keyword in content_lower or keyword in filename_lower:
                        score += 1
                category_scores[category] = score
            
            # Возвращаем категорию с наибольшим количеством совпадений
            if category_scores:
                best_category = max(category_scores, key=category_scores.get)
                if category_scores[best_category] > 0:
                    return best_category
            
            return DocumentCategory.OTHER
            
        except Exception as e:
            print(f"Ошибка категоризации документа: {e}")
            return DocumentCategory.OTHER
    
    def _extract_tags(self, content: str, filename: str) -> List[str]:
        """Извлечение тегов из содержимого"""
        try:
            tags = []
            content_lower = content.lower()
            filename_lower = filename.lower()
            
            # Предопределенные теги
            tag_patterns = {
                'важно': ['важно', 'important', 'срочно', 'urgent'],
                'конфиденциально': ['конфиденциально', 'confidential', 'секретно', 'secret'],
                'черновик': ['черновик', 'draft', 'набросок', 'sketch'],
                'финальная версия': ['финальная', 'final', 'окончательная', 'definitive'],
                'архив': ['архив', 'archive', 'старый', 'old'],
                'новый': ['новый', 'new', 'свежий', 'fresh'],
                'обновленный': ['обновленный', 'updated', 'измененный', 'modified']
            }
            
            for tag, keywords in tag_patterns.items():
                for keyword in keywords:
                    if keyword in content_lower or keyword in filename_lower:
                        tags.append(tag)
                        break
            
            # Извлекаем даты
            date_pattern = r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b'
            dates = re.findall(date_pattern, content)
            if dates:
                tags.append('с датой')
            
            # Извлекаем числа (суммы, количества)
            number_pattern = r'\b\d+(?:\.\d+)?\s*(?:руб|рублей|долл|долларов|евро|euro)\b'
            numbers = re.findall(number_pattern, content_lower)
            if numbers:
                tags.append('с суммой')
            
            return list(set(tags))  # убираем дубликаты
            
        except Exception as e:
            print(f"Ошибка извлечения тегов: {e}")
            return []
    
    def _generate_file_hash(self, file_path: str) -> str:
        """Генерация хеша файла"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            print(f"Ошибка генерации хеша файла: {e}")
            return ""
    
    def add_document(self, file_path: str, content: str = "", 
                    title: str = "", description: str = "", 
                    custom_tags: List[str] = None) -> str:
        """Добавление документа в каталог"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return None
            
            # Генерируем ID и хеш
            doc_id = str(uuid.uuid4())
            file_hash = self._generate_file_hash(file_path)
            
            # Проверяем, не существует ли уже такой документ
            for existing_doc in self.documents.values():
                if existing_doc.file_hash == file_hash:
                    return existing_doc.id
            
            # Определяем тип и категорию
            doc_type = self._detect_document_type(file_path_obj.name, content)
            category = self._categorize_document(content, file_path_obj.name)
            
            # Извлекаем теги
            auto_tags = self._extract_tags(content, file_path_obj.name)
            all_tags = (auto_tags or []) + (custom_tags or [])
            
            # Генерируем заголовок, если не указан
            if not title:
                title = file_path_obj.stem
            
            # Создаем превью содержимого
            content_preview = content[:500] if content else ""
            
            # Создаем документ
            document = Document(
                id=doc_id,
                filename=file_path_obj.name,
                file_path=str(file_path_obj.absolute()),
                file_size=file_path_obj.stat().st_size,
                document_type=doc_type,
                category=category,
                title=title,
                description=description,
                content_preview=content_preview,
                tags=all_tags,
                created_at=datetime.now(),
                modified_at=datetime.fromtimestamp(file_path_obj.stat().st_mtime),
                file_hash=file_hash,
                metadata={
                    'file_extension': file_path_obj.suffix,
                    'file_directory': str(file_path_obj.parent)
                }
            )
            
            self.documents[doc_id] = document
            self._save_documents()
            
            # Обновляем счетчики тегов
            self._update_tag_usage(all_tags)
            
            return doc_id
            
        except Exception as e:
            print(f"Ошибка добавления документа: {e}")
            return None
    
    def _update_tag_usage(self, tags: List[str]):
        """Обновление счетчиков использования тегов"""
        try:
            for tag_name in tags:
                # Ищем существующий тег
                existing_tag = None
                for tag in self.tags.values():
                    if tag.name == tag_name:
                        existing_tag = tag
                        break
                
                if existing_tag:
                    existing_tag.usage_count += 1
                else:
                    # Создаем новый тег
                    tag_id = str(uuid.uuid4())
                    new_tag = DocumentTag(
                        id=tag_id,
                        name=tag_name,
                        description=f"Автоматически созданный тег: {tag_name}",
                        color="#007bff",
                        created_at=datetime.now(),
                        usage_count=1
                    )
                    self.tags[tag_id] = new_tag
            
            self._save_tags()
            
        except Exception as e:
            print(f"Ошибка обновления счетчиков тегов: {e}")
    
    def search_documents(self, query: str, category: DocumentCategory = None, 
                        tags: List[str] = None, doc_type: DocumentType = None) -> List[Document]:
        """Поиск документов"""
        try:
            results = []
            query_lower = query.lower()
            
            for document in self.documents.values():
                # Фильтр по категории
                if category and document.category != category:
                    continue
                
                # Фильтр по типу
                if doc_type and document.document_type != doc_type:
                    continue
                
                # Фильтр по тегам
                if tags and not any(tag in document.tags for tag in tags):
                    continue
                
                # Поиск по содержимому
                if (query_lower in document.title.lower() or 
                    query_lower in document.description.lower() or 
                    query_lower in document.content_preview.lower() or
                    query_lower in document.filename.lower()):
                    results.append(document)
            
            return sorted(results, key=lambda x: x.modified_at, reverse=True)
            
        except Exception as e:
            print(f"Ошибка поиска документов: {e}")
            return []
    
    def get_documents_by_category(self, category: DocumentCategory) -> List[Document]:
        """Получение документов по категории"""
        try:
            return [doc for doc in self.documents.values() if doc.category == category]
        except Exception as e:
            print(f"Ошибка получения документов по категории: {e}")
            return []
    
    def get_documents_by_tag(self, tag: str) -> List[Document]:
        """Получение документов по тегу"""
        try:
            return [doc for doc in self.documents.values() if tag in doc.tags]
        except Exception as e:
            print(f"Ошибка получения документов по тегу: {e}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Получение документа по ID"""
        return self.documents.get(doc_id)
    
    def update_document(self, doc_id: str, title: str = None, description: str = None,
                       tags: List[str] = None, category: DocumentCategory = None) -> bool:
        """Обновление документа"""
        try:
            if doc_id not in self.documents:
                return False
            
            document = self.documents[doc_id]
            
            if title:
                document.title = title
            if description:
                document.description = description
            if tags:
                document.tags = tags
            if category:
                document.category = category
            
            document.modified_at = datetime.now()
            self._save_documents()
            
            return True
            
        except Exception as e:
            print(f"Ошибка обновления документа: {e}")
            return False
    
    def get_all_tags(self) -> List[DocumentTag]:
        """Получение всех тегов"""
        try:
            return sorted(self.tags.values(), key=lambda x: x.usage_count, reverse=True)
        except Exception as e:
            print(f"Ошибка получения тегов: {e}")
            return []
    
    def get_document_stats(self) -> Dict[str, Any]:
        """Получение статистики документов"""
        try:
            total_docs = len(self.documents)
            by_category = {}
            by_type = {}
            total_size = 0
            
            for document in self.documents.values():
                # По категориям
                category = document.category.value
                if category not in by_category:
                    by_category[category] = 0
                by_category[category] += 1
                
                # По типам
                doc_type = document.document_type.value
                if doc_type not in by_type:
                    by_type[doc_type] = 0
                by_type[doc_type] += 1
                
                total_size += document.file_size
            
            return {
                'total_documents': total_docs,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'by_category': by_category,
                'by_type': by_type,
                'total_tags': len(self.tags),
                'most_used_tags': [tag.name for tag in sorted(self.tags.values(), 
                                                            key=lambda x: x.usage_count, 
                                                            reverse=True)[:10]]
            }
        except Exception as e:
            print(f"Ошибка получения статистики документов: {e}")
            return {}
    
    def export_documents(self, format: str = "json") -> str:
        """Экспорт документов"""
        try:
            if format == "json":
                return json.dumps({d.id: asdict(d) for d in self.documents.values()}, 
                                 ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Title", "Filename", "Type", "Category", "Tags", "Size", "Created"])
                for document in self.documents.values():
                    writer.writerow([
                        document.title,
                        document.filename,
                        document.document_type.value,
                        document.category.value,
                        ", ".join(document.tags),
                        document.file_size,
                        document.created_at.strftime("%Y-%m-%d")
                    ])
                return output.getvalue()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта документов: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = DocAutocatalogService()
    
    # Добавляем тестовый документ
    doc_id = service.add_document(
        file_path="test_document.txt",
        content="Важный отчет по проекту. Срочно нужно завершить до 15.12.2024",
        title="Отчет по проекту",
        description="Еженедельный отчет"
    )
    
    print(f"Добавлен документ: {doc_id}")
    print(f"Статистика: {service.get_document_stats()}")
    print(f"Поиск 'отчет': {len(service.search_documents('отчет'))}")
