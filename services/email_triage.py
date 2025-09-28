# -*- coding: utf-8 -*-
"""
Email Triage Service - приоритезация писем
"""

import os
import json
import re
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import email
from email.header import decode_header

try:
    from brain.ai_client import BrainManager
    from integrations.yandex_translate import YandexTranslate
    BRAIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI компоненты недоступны: {e}")
    BRAIN_AVAILABLE = False


class EmailTriageService:
    """
    Сервис приоритезации писем
    """
    
    def __init__(self, storage_dir: str = "storage"):
        self.logger = logging.getLogger("EmailTriage")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Файлы данных
        self.emails_file = self.storage_dir / "emails.json"
        self.priorities_file = self.storage_dir / "priorities.json"
        self.rules_file = self.storage_dir / "triage_rules.json"
        
        # AI компоненты
        self.brain = None
        self.translate = None
        
        # Загружаем данные
        self.emails = self._load_emails()
        self.priorities = self._load_priorities()
        self.rules = self._load_rules()
        
        # Инициализация AI
        self._init_ai()
    
    def _init_ai(self):
        """Инициализация AI компонентов"""
        try:
            if BRAIN_AVAILABLE:
                self.brain = BrainManager()
                self.translate = YandexTranslate()
                self.logger.info("AI компоненты инициализированы")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации AI: {e}")
    
    def _load_emails(self) -> List[Dict[str, Any]]:
        """Загрузка писем из хранилища"""
        try:
            if self.emails_file.exists():
                with open(self.emails_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Ошибка загрузки писем: {e}")
            return []
    
    def _save_emails(self):
        """Сохранение писем"""
        try:
            with open(self.emails_file, 'w', encoding='utf-8') as f:
                json.dump(self.emails, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения писем: {e}")
    
    def _load_priorities(self) -> Dict[str, Any]:
        """Загрузка приоритетов"""
        try:
            if self.priorities_file.exists():
                with open(self.priorities_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "high": [],
                "medium": [],
                "low": [],
                "spam": []
            }
        except Exception as e:
            self.logger.error(f"Ошибка загрузки приоритетов: {e}")
            return {"high": [], "medium": [], "low": [], "spam": []}
    
    def _save_priorities(self):
        """Сохранение приоритетов"""
        try:
            with open(self.priorities_file, 'w', encoding='utf-8') as f:
                json.dump(self.priorities, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения приоритетов: {e}")
    
    def _load_rules(self) -> List[Dict[str, Any]]:
        """Загрузка правил приоритизации"""
        try:
            if self.rules_file.exists():
                with open(self.rules_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return self._get_default_rules()
        except Exception as e:
            self.logger.error(f"Ошибка загрузки правил: {e}")
            return self._get_default_rules()
    
    def _get_default_rules(self) -> List[Dict[str, Any]]:
        """Правила приоритизации по умолчанию"""
        return [
            {
                "name": "Высокий приоритет",
                "priority": "high",
                "conditions": [
                    {"field": "subject", "pattern": r"(срочно|urgent|важно|important)", "flags": "i"},
                    {"field": "from", "pattern": r"(boss|manager|director)", "flags": "i"},
                    {"field": "subject", "pattern": r"(deadline|дедлайн|срок)", "flags": "i"}
                ]
            },
            {
                "name": "Спам",
                "priority": "spam",
                "conditions": [
                    {"field": "subject", "pattern": r"(реклама|spam|рассылка)", "flags": "i"},
                    {"field": "from", "pattern": r"(noreply|no-reply|newsletter)", "flags": "i"}
                ]
            },
            {
                "name": "Средний приоритет",
                "priority": "medium",
                "conditions": [
                    {"field": "subject", "pattern": r"(встреча|meeting|обсуждение)", "flags": "i"},
                    {"field": "from", "pattern": r"(colleague|коллега)", "flags": "i"}
                ]
            }
        ]
    
    def _save_rules(self):
        """Сохранение правил"""
        try:
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения правил: {e}")
    
    def _parse_email_text(self, email_text: str) -> Dict[str, Any]:
        """Парсинг текста письма"""
        try:
            # Пытаемся распарсить как EML
            try:
                msg = email.message_from_string(email_text)
                
                # Извлекаем заголовки
                subject = self._decode_header(msg.get('Subject', ''))
                from_addr = self._decode_header(msg.get('From', ''))
                to_addr = self._decode_header(msg.get('To', ''))
                date_str = msg.get('Date', '')
                
                # Извлекаем тело письма
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                return {
                    "subject": subject,
                    "from": from_addr,
                    "to": to_addr,
                    "date": date_str,
                    "body": body,
                    "raw": email_text
                }
            except:
                # Если не EML, обрабатываем как простой текст
                lines = email_text.split('\n')
                subject = ""
                from_addr = ""
                body = email_text
                
                # Ищем заголовки в тексте
                for line in lines[:10]:  # Проверяем первые 10 строк
                    if line.lower().startswith('subject:'):
                        subject = line[8:].strip()
                    elif line.lower().startswith('from:'):
                        from_addr = line[5:].strip()
                
                return {
                    "subject": subject,
                    "from": from_addr,
                    "to": "",
                    "date": "",
                    "body": body,
                    "raw": email_text
                }
        except Exception as e:
            self.logger.error(f"Ошибка парсинга письма: {e}")
            return {
                "subject": "",
                "from": "",
                "to": "",
                "date": "",
                "body": email_text,
                "raw": email_text
            }
    
    def _decode_header(self, header: str) -> str:
        """Декодирование заголовка"""
        try:
            decoded_parts = decode_header(header)
            decoded_string = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            return decoded_string
        except Exception as e:
            self.logger.error(f"Ошибка декодирования заголовка: {e}")
            return header
    
    def _is_example_value(self, value: str) -> bool:
        """Проверка, является ли значение примером"""
        example_patterns = [
            r'your_.*',
            r'example_.*',
            r'test_.*',
            r'sample_.*',
            r'placeholder',
            r'xxx',
            r'123',
            r'000',
            r'fake',
            r'dummy'
        ]
        
        for pattern in example_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
    
    def _apply_rules(self, email_data: Dict[str, Any]) -> str:
        """Применение правил приоритизации"""
        try:
            for rule in self.rules:
                for condition in rule.get("conditions", []):
                    field = condition.get("field", "")
                    pattern = condition.get("pattern", "")
                    flags = 0
                    
                    if "i" in condition.get("flags", ""):
                        flags |= re.IGNORECASE
                    
                    if field in email_data:
                        if re.search(pattern, str(email_data[field]), flags):
                            return rule.get("priority", "medium")
            
            return "medium"  # По умолчанию средний приоритет
        except Exception as e:
            self.logger.error(f"Ошибка применения правил: {e}")
            return "medium"
    
    async def _ai_prioritize(self, email_data: Dict[str, Any]) -> Tuple[str, str]:
        """AI приоритизация письма"""
        try:
            if not self.brain:
                return "medium", "AI недоступен"
            
            # Формируем промпт для анализа
            prompt = f"""
Проанализируй письмо и определи его приоритет:

Тема: {email_data.get('subject', '')}
От: {email_data.get('from', '')}
Содержание: {email_data.get('body', '')[:500]}...

Определи приоритет: high, medium, low, spam
И дай краткое обоснование.

Ответ в формате: ПРИОРИТЕТ: [high/medium/low/spam]
ОБОСНОВАНИЕ: [краткое объяснение]
            """
            
            response = await self.brain.generate_response(prompt)
            
            # Парсим ответ
            priority = "medium"
            reasoning = "AI анализ недоступен"
            
            if "ПРИОРИТЕТ:" in response:
                priority_line = [line for line in response.split('\n') if 'ПРИОРИТЕТ:' in line]
                if priority_line:
                    priority = priority_line[0].split(':')[1].strip().lower()
            
            if "ОБОСНОВАНИЕ:" in response:
                reasoning_line = [line for line in response.split('\n') if 'ОБОСНОВАНИЕ:' in line]
                if reasoning_line:
                    reasoning = reasoning_line[0].split(':')[1].strip()
            
            return priority, reasoning
            
        except Exception as e:
            self.logger.error(f"Ошибка AI приоритизации: {e}")
            return "medium", f"Ошибка: {str(e)}"
    
    async def process_email(self, email_text: str, use_ai: bool = True) -> Dict[str, Any]:
        """Обработка письма"""
        try:
            # Парсим письмо
            email_data = self._parse_email_text(email_text)
            
            # Определяем приоритет
            if use_ai and self.brain:
                priority, reasoning = await self._ai_prioritize(email_data)
            else:
                priority = self._apply_rules(email_data)
                reasoning = "Правила приоритизации"
            
            # Создаем запись
            email_record = {
                "id": f"email_{len(self.emails) + 1}",
                "timestamp": datetime.now().isoformat(),
                "subject": email_data.get("subject", ""),
                "from": email_data.get("from", ""),
                "to": email_data.get("to", ""),
                "date": email_data.get("date", ""),
                "body": email_data.get("body", "")[:1000],  # Ограничиваем размер
                "priority": priority,
                "reasoning": reasoning,
                "processed": True
            }
            
            # Добавляем в хранилище
            self.emails.append(email_record)
            self._save_emails()
            
            # Обновляем приоритеты
            if priority not in self.priorities:
                self.priorities[priority] = []
            self.priorities[priority].append(email_record["id"])
            self._save_priorities()
            
            return email_record
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки письма: {e}")
            return {
                "id": f"error_{len(self.emails) + 1}",
                "error": str(e),
                "priority": "low",
                "reasoning": "Ошибка обработки"
            }
    
    def get_priorities_summary(self) -> Dict[str, Any]:
        """Получение сводки по приоритетам"""
        try:
            summary = {
                "total_emails": len(self.emails),
                "by_priority": {},
                "recent_high": [],
                "unprocessed": []
            }
            
            # Подсчитываем по приоритетам
            for priority, email_ids in self.priorities.items():
                summary["by_priority"][priority] = len(email_ids)
            
            # Недавние высокоприоритетные
            recent_high = [
                email for email in self.emails 
                if email.get("priority") == "high" 
                and datetime.fromisoformat(email.get("timestamp", "1970-01-01")) > datetime.now() - timedelta(days=1)
            ]
            summary["recent_high"] = recent_high[:5]  # Последние 5
            
            # Необработанные
            unprocessed = [email for email in self.emails if not email.get("processed", False)]
            summary["unprocessed"] = unprocessed[:10]  # Последние 10
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки: {e}")
            return {"error": str(e)}
    
    def get_emails_by_priority(self, priority: str) -> List[Dict[str, Any]]:
        """Получение писем по приоритету"""
        try:
            email_ids = self.priorities.get(priority, [])
            emails = [email for email in self.emails if email["id"] in email_ids]
            return sorted(emails, key=lambda x: x.get("timestamp", ""), reverse=True)
        except Exception as e:
            self.logger.error(f"Ошибка получения писем по приоритету: {e}")
            return []
    
    def add_rule(self, rule: Dict[str, Any]) -> bool:
        """Добавление правила приоритизации"""
        try:
            self.rules.append(rule)
            self._save_rules()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка добавления правила: {e}")
            return False
    
    def remove_rule(self, rule_name: str) -> bool:
        """Удаление правила"""
        try:
            self.rules = [rule for rule in self.rules if rule.get("name") != rule_name]
            self._save_rules()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка удаления правила: {e}")
            return False
    
    def export_priorities(self, format: str = "json") -> str:
        """Экспорт приоритетов"""
        try:
            if format == "json":
                return json.dumps(self.priorities, ensure_ascii=False, indent=2)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Priority", "Email ID", "Subject", "From", "Timestamp"])
                
                for priority, email_ids in self.priorities.items():
                    for email_id in email_ids:
                        email_data = next((e for e in self.emails if e["id"] == email_id), {})
                        writer.writerow([
                            priority,
                            email_id,
                            email_data.get("subject", ""),
                            email_data.get("from", ""),
                            email_data.get("timestamp", "")
                        ])
                
                return output.getvalue()
            else:
                return "Неподдерживаемый формат"
        except Exception as e:
            self.logger.error(f"Ошибка экспорта: {e}")
            return f"Ошибка: {str(e)}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            "total_emails": len(self.emails),
            "rules_count": len(self.rules),
            "priorities": {k: len(v) for k, v in self.priorities.items()},
            "ai_available": self.brain is not None,
            "translate_available": self.translate is not None
        }


# Функция для тестирования
async def test_email_triage():
    """Тестирование сервиса приоритезации писем"""
    triage = EmailTriageService()
    
    print("Testing Email Triage Service...")
    
    # Тестовое письмо
    test_email = """
Subject: Срочно! Дедлайн проекта завтра
From: boss@company.com
To: me@company.com

Привет! Нужно срочно доделать проект до завтра.
Это очень важно для клиента.
    """
    
    # Обрабатываем письмо
    result = await triage.process_email(test_email)
    print(f"Processed email: {result}")
    
    # Получаем сводку
    summary = triage.get_priorities_summary()
    print(f"Summary: {summary}")
    
    # Статистика
    stats = triage.get_stats()
    print(f"Stats: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_email_triage())
