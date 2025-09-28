# -*- coding: utf-8 -*-
"""
Умная почта и авто-шаблоны
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from mail_calendar import MailCalendar
    from brain.ai_client import BrainManager
    from memory_palace import MemoryPalace
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


class EmailCategory(Enum):
    """Категории писем"""
    IMPORTANT = "important"
    PENDING_REPLY = "pending_reply"
    BILL = "bill"
    SPAM = "spam"
    JOB_RELATED = "job_related"
    PERSONAL = "personal"
    NEWS = "news"
    UNKNOWN = "unknown"


@dataclass
class EmailTemplate:
    """Шаблон ответа"""
    name: str
    category: EmailCategory
    subject_pattern: str
    body_template: str
    auto_reply: bool = False
    priority: int = 1


@dataclass
class EmailAnalysis:
    """Анализ письма"""
    category: EmailCategory
    priority: int
    requires_reply: bool
    suggested_template: Optional[str]
    key_info: Dict[str, Any]
    sentiment: str  # positive, negative, neutral


class SmartMail:
    """
    Умная почта с классификацией и авто-шаблонами
    """
    
    def __init__(self):
        self.logger = logging.getLogger("SmartMail")
        
        # Компоненты
        self.mail_calendar = None
        self.brain_manager = None
        self.memory_palace = None
        
        # Шаблоны ответов
        self.templates = self._load_templates()
        
        # Паттерны для классификации
        self.patterns = self._load_patterns()
        
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
            
            # Brain Manager для анализа
            self.brain_manager = BrainManager()
            
            # Memory Palace
            self.memory_palace = MemoryPalace()
            
            self.logger.info("Компоненты Smart Mail инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    def _load_templates(self) -> List[EmailTemplate]:
        """Загрузка шаблонов ответов"""
        templates = [
            EmailTemplate(
                name="Подтверждение встречи",
                category=EmailCategory.JOB_RELATED,
                subject_pattern=r"(встреча|интервью|собеседование)",
                body_template="""Здравствуйте!

Спасибо за приглашение на {meeting_type}. 
Подтверждаю встречу на {date} в {time}.

С уважением,
Максим Онюшко""",
                auto_reply=False,
                priority=1
            ),
            EmailTemplate(
                name="Отказ от предложения",
                category=EmailCategory.JOB_RELATED,
                subject_pattern=r"(отказ|отклонение)",
                body_template="""Здравствуйте!

Благодарю за предложение, но вынужден отказаться.
{reason}

С уважением,
Максим Онюшко""",
                auto_reply=False,
                priority=2
            ),
            EmailTemplate(
                name="Запрос информации",
                category=EmailCategory.PENDING_REPLY,
                subject_pattern=r"(вопрос|информация|уточнение)",
                body_template="""Здравствуйте!

По поводу вашего вопроса: {question}

{answer}

Если нужны дополнительные детали, готов обсудить.

С уважением,
Максим Онюшко""",
                auto_reply=False,
                priority=1
            ),
            EmailTemplate(
                name="Автоответ офлайн",
                category=EmailCategory.PERSONAL,
                subject_pattern=r".*",
                body_template="""Здравствуйте!

Спасибо за письмо. В данный момент я недоступен и отвечу в ближайшее время.

С уважением,
Максим Онюшко""",
                auto_reply=True,
                priority=3
            )
        ]
        
        return templates
    
    def _load_patterns(self) -> Dict[EmailCategory, List[str]]:
        """Загрузка паттернов для классификации"""
        return {
            EmailCategory.IMPORTANT: [
                r"(срочно|urgent|важно|important)",
                r"(дедлайн|deadline|срок)",
                r"(контракт|contract|соглашение)"
            ],
            EmailCategory.PENDING_REPLY: [
                r"(ответ|reply|ответьте)",
                r"(вопрос|question|уточнение)",
                r"(подтверждение|confirmation)"
            ],
            EmailCategory.BILL: [
                r"(счет|bill|invoice|платеж)",
                r"(оплата|payment|деньги)",
                r"(банк|bank|карта)"
            ],
            EmailCategory.SPAM: [
                r"(реклама|advertisement|promo)",
                r"(рассылка|newsletter|массовая)",
                r"(виагра|casino|лотерея)"
            ],
            EmailCategory.JOB_RELATED: [
                r"(работа|job|вакансия|vacancy)",
                r"(собеседование|interview|встреча)",
                r"(резюме|cv|curriculum)"
            ],
            EmailCategory.PERSONAL: [
                r"(семья|family|друзья|friends)",
                r"(личное|personal|приватное)"
            ],
            EmailCategory.NEWS: [
                r"(новости|news|обновления)",
                r"(блог|blog|статья)"
            ]
        }
    
    async def analyze_email(self, email_data: Dict[str, Any]) -> EmailAnalysis:
        """Анализ письма"""
        try:
            subject = email_data.get('subject', '').lower()
            body = email_data.get('body', '').lower()
            sender = email_data.get('from', '').lower()
            
            # Определяем категорию
            category = self._classify_email(subject, body, sender)
            
            # Определяем приоритет
            priority = self._calculate_priority(email_data, category)
            
            # Требует ли ответа
            requires_reply = self._requires_reply(subject, body)
            
            # Подходящий шаблон
            suggested_template = self._find_template(category, subject)
            
            # Ключевая информация
            key_info = self._extract_key_info(email_data)
            
            # Тональность
            sentiment = self._analyze_sentiment(body)
            
            return EmailAnalysis(
                category=category,
                priority=priority,
                requires_reply=requires_reply,
                suggested_template=suggested_template,
                key_info=key_info,
                sentiment=sentiment
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка анализа письма: {e}")
            return EmailAnalysis(
                category=EmailCategory.UNKNOWN,
                priority=1,
                requires_reply=False,
                suggested_template=None,
                key_info={},
                sentiment="neutral"
            )
    
    def _classify_email(self, subject: str, body: str, sender: str) -> EmailCategory:
        """Классификация письма"""
        text = f"{subject} {body}"
        
        # Проверяем каждый паттерн
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return category
        
        return EmailCategory.UNKNOWN
    
    def _calculate_priority(self, email_data: Dict, category: EmailCategory) -> int:
        """Расчет приоритета"""
        priority = 1
        
        # Важные категории
        if category == EmailCategory.IMPORTANT:
            priority = 5
        elif category == EmailCategory.JOB_RELATED:
            priority = 4
        elif category == EmailCategory.PENDING_REPLY:
            priority = 3
        elif category == EmailCategory.BILL:
            priority = 2
        
        # Дополнительные факторы
        if email_data.get('unread', False):
            priority += 1
        
        if 'urgent' in email_data.get('subject', '').lower():
            priority += 2
        
        return min(priority, 5)
    
    def _requires_reply(self, subject: str, body: str) -> bool:
        """Определение необходимости ответа"""
        reply_indicators = [
            r"(ответ|reply|ответьте)",
            r"(вопрос|question)",
            r"(подтверждение|confirmation)",
            r"(согласие|agreement)",
            r"(встреча|meeting)"
        ]
        
        text = f"{subject} {body}"
        for pattern in reply_indicators:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _find_template(self, category: EmailCategory, subject: str) -> Optional[str]:
        """Поиск подходящего шаблона"""
        for template in self.templates:
            if template.category == category:
                if re.search(template.subject_pattern, subject, re.IGNORECASE):
                    return template.name
        
        return None
    
    def _extract_key_info(self, email_data: Dict) -> Dict[str, Any]:
        """Извлечение ключевой информации"""
        key_info = {}
        
        # Даты
        date_patterns = [
            r'(\d{1,2}[./]\d{1,2}[./]\d{2,4})',
            r'(\d{1,2}\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря))'
        ]
        
        text = f"{email_data.get('subject', '')} {email_data.get('body', '')}"
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                key_info['dates'] = matches
        
        # Время
        time_pattern = r'(\d{1,2}:\d{2})'
        time_matches = re.findall(time_pattern, text)
        if time_matches:
            key_info['times'] = time_matches
        
        # Суммы
        money_pattern = r'(\d+[\s,]*\d*\s*(руб|₽|рублей|долларов|$|€))'
        money_matches = re.findall(money_pattern, text, re.IGNORECASE)
        if money_matches:
            key_info['amounts'] = money_matches
        
        return key_info
    
    def _analyze_sentiment(self, body: str) -> str:
        """Анализ тональности"""
        positive_words = ['спасибо', 'благодарю', 'отлично', 'хорошо', 'успех']
        negative_words = ['проблема', 'ошибка', 'отказ', 'неправильно', 'плохо']
        
        positive_count = sum(1 for word in positive_words if word in body.lower())
        negative_count = sum(1 for word in negative_words if word in body.lower())
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    async def generate_reply(self, email_data: Dict, template_name: str, custom_data: Dict = None) -> str:
        """Генерация ответа по шаблону"""
        try:
            # Находим шаблон
            template = None
            for t in self.templates:
                if t.name == template_name:
                    template = t
                    break
            
            if not template:
                return "Шаблон не найден"
            
            # Заполняем шаблон
            reply = template.body_template
            
            # Заменяем переменные
            if custom_data:
                for key, value in custom_data.items():
                    reply = reply.replace(f"{{{key}}}", str(value))
            
            # Автоматические замены
            reply = reply.replace("{meeting_type}", "встречу")
            reply = reply.replace("{date}", datetime.now().strftime("%d.%m.%Y"))
            reply = reply.replace("{time}", "в удобное время")
            
            return reply
            
        except Exception as e:
            self.logger.error(f"Ошибка генерации ответа: {e}")
            return "Ошибка генерации ответа"
    
    async def get_email_summary(self) -> Dict[str, Any]:
        """Сводка по почте"""
        try:
            if not self.mail_calendar:
                return {"error": "Mail Calendar недоступен"}
            
            emails = await self.mail_calendar.check_emails()
            
            # Анализируем каждое письмо
            categories = {}
            priorities = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            requires_reply = 0
            
            for email in emails:
                analysis = await self.analyze_email(email)
                
                # Категории
                cat_name = analysis.category.value
                categories[cat_name] = categories.get(cat_name, 0) + 1
                
                # Приоритеты
                priorities[analysis.priority] += 1
                
                # Требуют ответа
                if analysis.requires_reply:
                    requires_reply += 1
            
            return {
                "total_emails": len(emails),
                "categories": categories,
                "priorities": priorities,
                "requires_reply": requires_reply,
                "unread": len([e for e in emails if not e.get('read', False)])
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения сводки: {e}")
            return {"error": str(e)}
    
    def format_email_analysis(self, analysis: EmailAnalysis) -> str:
        """Форматирование анализа письма"""
        text = f"📧 <b>Анализ письма</b>\n\n"
        text += f"🏷️ Категория: {analysis.category.value}\n"
        text += f"⭐ Приоритет: {analysis.priority}/5\n"
        text += f"💬 Тональность: {analysis.sentiment}\n"
        text += f"📝 Требует ответа: {'Да' if analysis.requires_reply else 'Нет'}\n"
        
        if analysis.suggested_template:
            text += f"📋 Рекомендуемый шаблон: {analysis.suggested_template}\n"
        
        if analysis.key_info:
            text += f"\n🔍 <b>Ключевая информация:</b>\n"
            for key, value in analysis.key_info.items():
                text += f"• {key}: {value}\n"
        
        return text


# Функция для тестирования
async def test_smart_mail():
    """Тестирование умной почты"""
    smart_mail = SmartMail()
    
    # Тестовое письмо
    test_email = {
        'subject': 'Встреча по поводу собеседования',
        'body': 'Здравствуйте! Предлагаю встретиться завтра в 14:00 для обсуждения позиции Python разработчика.',
        'from': 'hr@company.com',
        'unread': True
    }
    
    # Анализ
    analysis = await smart_mail.analyze_email(test_email)
    print("Анализ письма:")
    print(smart_mail.format_email_analysis(analysis))
    
    # Генерация ответа
    reply = await smart_mail.generate_reply(test_email, "Подтверждение встречи", {
        "meeting_type": "собеседование",
        "date": "завтра",
        "time": "14:00"
    })
    print("\nСгенерированный ответ:")
    print(reply)


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_smart_mail())
