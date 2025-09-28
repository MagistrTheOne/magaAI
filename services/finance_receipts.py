# -*- coding: utf-8 -*-
"""
Finance Receipts Service - обработка чеков и финансов
"""

import os
import json
import csv
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import uuid
import re

try:
    from brain.ai_client import BrainManager
    from integrations.yandex_ocr import YandexOCR
    BRAIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI компоненты недоступны: {e}")
    BRAIN_AVAILABLE = False


class FinanceReceiptsService:
    """
    Сервис обработки чеков и финансов
    """
    
    def __init__(self, storage_dir: str = "storage"):
        self.logger = logging.getLogger("FinanceReceipts")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Файлы данных
        self.receipts_file = self.storage_dir / "receipts.json"
        self.categories_file = self.storage_dir / "categories.json"
        self.expenses_file = self.storage_dir / "expenses.json"
        
        # AI компоненты
        self.brain = None
        self.ocr = None
        
        # Загружаем данные
        self.receipts = self._load_receipts()
        self.categories = self._load_categories()
        self.expenses = self._load_expenses()
        
        # Инициализация AI
        self._init_ai()
    
    def _init_ai(self):
        """Инициализация AI компонентов"""
        try:
            if BRAIN_AVAILABLE:
                self.brain = BrainManager()
                self.ocr = YandexOCR()
                self.logger.info("AI компоненты инициализированы")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации AI: {e}")
    
    def _load_receipts(self) -> List[Dict[str, Any]]:
        """Загрузка чеков"""
        try:
            if self.receipts_file.exists():
                with open(self.receipts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Ошибка загрузки чеков: {e}")
            return []
    
    def _save_receipts(self):
        """Сохранение чеков"""
        try:
            with open(self.receipts_file, 'w', encoding='utf-8') as f:
                json.dump(self.receipts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения чеков: {e}")
    
    def _load_categories(self) -> Dict[str, Any]:
        """Загрузка категорий"""
        try:
            if self.categories_file.exists():
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self._get_default_categories()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки категорий: {e}")
            return self._get_default_categories()
    
    def _get_default_categories(self) -> Dict[str, Any]:
        """Категории по умолчанию"""
        return {
            "food": {
                "name": "Еда и напитки",
                "keywords": ["продукты", "кафе", "ресторан", "еда", "напитки", "супермаркет"],
                "color": "#FF6B6B"
            },
            "transport": {
                "name": "Транспорт",
                "keywords": ["бензин", "такси", "метро", "автобус", "поезд", "самолет"],
                "color": "#4ECDC4"
            },
            "health": {
                "name": "Здоровье",
                "keywords": ["аптека", "врач", "лекарства", "медицина", "спорт"],
                "color": "#45B7D1"
            },
            "shopping": {
                "name": "Покупки",
                "keywords": ["магазин", "одежда", "электроника", "книги", "подарки"],
                "color": "#96CEB4"
            },
            "utilities": {
                "name": "Коммунальные услуги",
                "keywords": ["электричество", "газ", "вода", "интернет", "телефон"],
                "color": "#FFEAA7"
            },
            "entertainment": {
                "name": "Развлечения",
                "keywords": ["кино", "театр", "игры", "отдых", "хобби"],
                "color": "#DDA0DD"
            },
            "other": {
                "name": "Прочее",
                "keywords": [],
                "color": "#95A5A6"
            }
        }
    
    def _save_categories(self):
        """Сохранение категорий"""
        try:
            with open(self.categories_file, 'w', encoding='utf-8') as f:
                json.dump(self.categories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения категорий: {e}")
    
    def _load_expenses(self) -> List[Dict[str, Any]]:
        """Загрузка расходов"""
        try:
            if self.expenses_file.exists():
                with open(self.expenses_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Ошибка загрузки расходов: {e}")
            return []
    
    def _save_expenses(self):
        """Сохранение расходов"""
        try:
            with open(self.expenses_file, 'w', encoding='utf-8') as f:
                json.dump(self.expenses, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения расходов: {e}")
    
    def _extract_amount_from_text(self, text: str) -> Optional[float]:
        """Извлечение суммы из текста"""
        try:
            # Ищем суммы в различных форматах
            patterns = [
                r'(\d+[.,]\d{2})\s*руб',
                r'(\d+[.,]\d{2})\s*₽',
                r'(\d+[.,]\d{2})\s*р',
                r'(\d+[.,]\d{2})',
                r'(\d+)\s*руб',
                r'(\d+)\s*₽',
                r'(\d+)\s*р'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    amount_str = matches[0].replace(',', '.')
                    return float(amount_str)
            
            return None
        except Exception as e:
            self.logger.error(f"Ошибка извлечения суммы: {e}")
            return None
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """Извлечение даты из текста"""
        try:
            # Ищем даты в различных форматах
            patterns = [
                r'(\d{1,2}[./]\d{1,2}[./]\d{4})',
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{1,2}\s+\w+\s+\d{4})'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    return matches[0]
            
            return None
        except Exception as e:
            self.logger.error(f"Ошибка извлечения даты: {e}")
            return None
    
    async def _ai_categorize_expense(self, text: str, amount: float) -> Tuple[str, str]:
        """AI категоризация расхода"""
        try:
            if not self.brain:
                return "other", "AI недоступен"
            
            # Формируем промпт
            prompt = f"""
Проанализируй расход и определи категорию:

Текст: {text}
Сумма: {amount} руб

Доступные категории:
- food: Еда и напитки
- transport: Транспорт  
- health: Здоровье
- shopping: Покупки
- utilities: Коммунальные услуги
- entertainment: Развлечения
- other: Прочее

Верни только код категории и краткое обоснование в формате:
КАТЕГОРИЯ: [код]
ОБОСНОВАНИЕ: [краткое объяснение]
            """
            
            response = await self.brain.generate_response(prompt)
            
            # Парсим ответ
            category = "other"
            reasoning = "AI анализ недоступен"
            
            if "КАТЕГОРИЯ:" in response:
                category_line = [line for line in response.split('\n') if 'КАТЕГОРИЯ:' in line]
                if category_line:
                    category = category_line[0].split(':')[1].strip()
            
            if "ОБОСНОВАНИЕ:" in response:
                reasoning_line = [line for line in response.split('\n') if 'ОБОСНОВАНИЕ:' in line]
                if reasoning_line:
                    reasoning = reasoning_line[0].split(':')[1].strip()
            
            return category, reasoning
            
        except Exception as e:
            self.logger.error(f"Ошибка AI категоризации: {e}")
            return "other", f"Ошибка: {str(e)}"
    
    def _categorize_expense(self, text: str, amount: float) -> Tuple[str, str]:
        """Категоризация расхода по ключевым словам"""
        try:
            text_lower = text.lower()
            
            for category_id, category_data in self.categories.items():
                keywords = category_data.get("keywords", [])
                for keyword in keywords:
                    if keyword.lower() in text_lower:
                        return category_id, f"Найдено ключевое слово: {keyword}"
            
            return "other", "Не удалось определить категорию"
        except Exception as e:
            self.logger.error(f"Ошибка категоризации: {e}")
            return "other", f"Ошибка: {str(e)}"
    
    async def process_receipt(self, receipt_text: str, use_ai: bool = True) -> Dict[str, Any]:
        """Обработка чека"""
        try:
            # Извлекаем данные из текста
            amount = self._extract_amount_from_text(receipt_text)
            date_str = self._extract_date_from_text(receipt_text)
            
            if not amount:
                return {"error": "Не удалось извлечь сумму из чека"}
            
            # Категоризация
            if use_ai and self.brain:
                category, reasoning = await self._ai_categorize_expense(receipt_text, amount)
            else:
                category, reasoning = self._categorize_expense(receipt_text, amount)
            
            # Создаем запись чека
            receipt_id = str(uuid.uuid4())
            receipt = {
                "id": receipt_id,
                "text": receipt_text,
                "amount": amount,
                "date": date_str or datetime.now().strftime("%Y-%m-%d"),
                "category": category,
                "reasoning": reasoning,
                "processed_at": datetime.now().isoformat()
            }
            
            self.receipts.append(receipt)
            self._save_receipts()
            
            # Создаем запись расхода
            expense = {
                "id": str(uuid.uuid4()),
                "receipt_id": receipt_id,
                "amount": amount,
                "date": receipt["date"],
                "category": category,
                "description": receipt_text[:100] + "..." if len(receipt_text) > 100 else receipt_text,
                "created_at": datetime.now().isoformat()
            }
            
            self.expenses.append(expense)
            self._save_expenses()
            
            return receipt
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки чека: {e}")
            return {"error": str(e)}
    
    def get_expenses_by_category(self, category: str = None, 
                                start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """Получение расходов по категории и дате"""
        try:
            filtered_expenses = self.expenses.copy()
            
            if category:
                filtered_expenses = [e for e in filtered_expenses if e.get("category") == category]
            
            if start_date:
                filtered_expenses = [e for e in filtered_expenses if e.get("date") >= start_date]
            
            if end_date:
                filtered_expenses = [e for e in filtered_expenses if e.get("date") <= end_date]
            
            # Сортируем по дате
            filtered_expenses.sort(key=lambda x: x.get("date", ""), reverse=True)
            
            return filtered_expenses
        except Exception as e:
            self.logger.error(f"Ошибка получения расходов: {e}")
            return []
    
    def get_expenses_summary(self, period: str = "month") -> Dict[str, Any]:
        """Получение сводки по расходам"""
        try:
            # Определяем период
            if period == "week":
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            elif period == "month":
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            elif period == "year":
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            else:
                start_date = None
            
            # Получаем расходы за период
            expenses = self.get_expenses_by_category(start_date=start_date)
            
            # Подсчитываем по категориям
            category_totals = {}
            total_amount = 0
            
            for expense in expenses:
                category = expense.get("category", "other")
                amount = expense.get("amount", 0)
                
                if category not in category_totals:
                    category_totals[category] = 0
                
                category_totals[category] += amount
                total_amount += amount
            
            # Топ категории
            top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "period": period,
                "total_amount": total_amount,
                "expenses_count": len(expenses),
                "category_totals": category_totals,
                "top_categories": top_categories[:5],
                "average_daily": total_amount / max(1, len(set(e.get("date", "") for e in expenses)))
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки: {e}")
            return {"error": str(e)}
    
    def export_expenses_csv(self, start_date: str = None, end_date: str = None) -> str:
        """Экспорт расходов в CSV"""
        try:
            expenses = self.get_expenses_by_category(start_date=start_date, end_date=end_date)
            
            output = []
            output.append("Date,Category,Amount,Description")
            
            for expense in expenses:
                output.append(f"{expense.get('date', '')},{expense.get('category', '')},{expense.get('amount', 0)},{expense.get('description', '')}")
            
            return "\n".join(output)
        except Exception as e:
            self.logger.error(f"Ошибка экспорта CSV: {e}")
            return f"Ошибка: {str(e)}"
    
    def add_category(self, category_id: str, name: str, keywords: List[str], color: str = "#95A5A6") -> bool:
        """Добавление категории"""
        try:
            self.categories[category_id] = {
                "name": name,
                "keywords": keywords,
                "color": color
            }
            self._save_categories()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка добавления категории: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            "total_receipts": len(self.receipts),
            "total_expenses": len(self.expenses),
            "categories_count": len(self.categories),
            "ai_available": self.brain is not None,
            "ocr_available": self.ocr is not None,
            "total_amount": sum(e.get("amount", 0) for e in self.expenses)
        }


# Функция для тестирования
async def test_finance_receipts():
    """Тестирование сервиса финансов"""
    service = FinanceReceiptsService()
    
    print("Testing Finance Receipts Service...")
    
    # Тестовый чек
    test_receipt = """
    ЧЕК №12345
    Дата: 28.09.2024
    Время: 14:30
    
    Продукты:
    Хлеб - 50.00 руб
    Молоко - 80.00 руб
    Сыр - 200.00 руб
    
    ИТОГО: 330.00 руб
    """
    
    # Обрабатываем чек
    result = await service.process_receipt(test_receipt)
    print(f"Processed receipt: {result}")
    
    # Получаем сводку
    summary = service.get_expenses_summary("month")
    print(f"Summary: {summary}")
    
    # Экспортируем в CSV
    csv_data = service.export_expenses_csv()
    print(f"CSV export: {csv_data}")
    
    # Статистика
    stats = service.get_stats()
    print(f"Stats: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_finance_receipts())
