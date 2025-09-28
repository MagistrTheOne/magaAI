# -*- coding: utf-8 -*-
"""
Личный CRM - нетворкинг и управление контактами
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

try:
    from memory_palace import MemoryPalace
    from mail_calendar import MailCalendar
    from brain.ai_client import BrainManager
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


class ContactStatus(Enum):
    """Статус контакта"""
    NEW = "new"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    MEETING_SCHEDULED = "meeting_scheduled"
    FOLLOW_UP_NEEDED = "follow_up_needed"
    RELATIONSHIP_ESTABLISHED = "relationship_established"
    COLD = "cold"


class InteractionType(Enum):
    """Тип взаимодействия"""
    EMAIL = "email"
    PHONE = "phone"
    MEETING = "meeting"
    LINKEDIN = "linkedin"
    SOCIAL = "social"
    REFERRAL = "referral"


@dataclass
class Contact:
    """Контакт"""
    id: str
    name: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    position: Optional[str]
    linkedin: Optional[str]
    status: ContactStatus
    tags: List[str]
    notes: str
    created_at: str
    last_contact: Optional[str]
    next_follow_up: Optional[str]
    source: str  # откуда узнали о контакте


@dataclass
class Interaction:
    """Взаимодействие"""
    id: str
    contact_id: str
    type: InteractionType
    date: str
    content: str
    outcome: str
    next_action: Optional[str]
    important: bool = False


@dataclass
class FollowUpReminder:
    """Напоминание о follow-up"""
    contact_id: str
    contact_name: str
    due_date: str
    reason: str
    priority: int  # 1-5
    completed: bool = False


class PersonalCRM:
    """
    Личный CRM для нетворкинга
    """
    
    def __init__(self):
        self.logger = logging.getLogger("PersonalCRM")
        
        # Компоненты
        self.memory_palace = None
        self.mail_calendar = None
        self.brain_manager = None
        
        # Данные
        self.contacts: Dict[str, Contact] = {}
        self.interactions: Dict[str, List[Interaction]] = {}
        self.follow_up_reminders: List[FollowUpReminder] = []
        
        # Настройки
        self.config = {
            'auto_follow_up_days': 7,
            'max_contacts': 1000,
            'reminder_priority_threshold': 3
        }
        
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
            
            # Mail Calendar
            self.mail_calendar = MailCalendar()
            
            # Brain Manager
            self.brain_manager = BrainManager()
            
            self.logger.info("Компоненты Personal CRM инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    async def add_contact(self, contact_data: Dict[str, Any]) -> str:
        """Добавление контакта"""
        try:
            contact_id = f"contact_{len(self.contacts) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            contact = Contact(
                id=contact_id,
                name=contact_data.get('name', ''),
                email=contact_data.get('email'),
                phone=contact_data.get('phone'),
                company=contact_data.get('company'),
                position=contact_data.get('position'),
                linkedin=contact_data.get('linkedin'),
                status=ContactStatus.NEW,
                tags=contact_data.get('tags', []),
                notes=contact_data.get('notes', ''),
                created_at=datetime.now().isoformat(),
                last_contact=None,
                next_follow_up=None,
                source=contact_data.get('source', 'manual')
            )
            
            self.contacts[contact_id] = contact
            self.interactions[contact_id] = []
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"Добавлен контакт: {contact.name} из {contact.company}",
                    metadata={
                        'type': 'contact_added',
                        'contact_id': contact_id,
                        'company': contact.company,
                        'position': contact.position
                    }
                )
            
            self.logger.info(f"Добавлен контакт: {contact.name}")
            return contact_id
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления контакта: {e}")
            return None
    
    async def add_interaction(self, contact_id: str, interaction_data: Dict[str, Any]) -> str:
        """Добавление взаимодействия"""
        try:
            if contact_id not in self.contacts:
                self.logger.error(f"Контакт {contact_id} не найден")
                return None
            
            interaction_id = f"interaction_{len(self.interactions[contact_id]) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            interaction = Interaction(
                id=interaction_id,
                contact_id=contact_id,
                type=InteractionType(interaction_data.get('type', 'email')),
                date=datetime.now().isoformat(),
                content=interaction_data.get('content', ''),
                outcome=interaction_data.get('outcome', ''),
                next_action=interaction_data.get('next_action'),
                important=interaction_data.get('important', False)
            )
            
            self.interactions[contact_id].append(interaction)
            
            # Обновляем статус контакта
            await self._update_contact_status(contact_id, interaction)
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"Взаимодействие с {self.contacts[contact_id].name}: {interaction.content}",
                    metadata={
                        'type': 'interaction',
                        'contact_id': contact_id,
                        'interaction_type': interaction.type.value,
                        'outcome': interaction.outcome
                    }
                )
            
            self.logger.info(f"Добавлено взаимодействие с {self.contacts[contact_id].name}")
            return interaction_id
            
        except Exception as e:
            self.logger.error(f"Ошибка добавления взаимодействия: {e}")
            return None
    
    async def _update_contact_status(self, contact_id: str, interaction: Interaction):
        """Обновление статуса контакта"""
        contact = self.contacts[contact_id]
        
        # Обновляем последний контакт
        contact.last_contact = interaction.date
        
        # Обновляем статус на основе типа взаимодействия
        if interaction.type == InteractionType.EMAIL:
            if contact.status == ContactStatus.NEW:
                contact.status = ContactStatus.CONTACTED
        elif interaction.type == InteractionType.MEETING:
            contact.status = ContactStatus.MEETING_SCHEDULED
        elif interaction.type == InteractionType.PHONE:
            contact.status = ContactStatus.RESPONDED
        
        # Планируем follow-up если нужно
        if interaction.next_action:
            follow_up_date = datetime.now() + timedelta(days=self.config['auto_follow_up_days'])
            contact.next_follow_up = follow_up_date.isoformat()
            
            # Добавляем напоминание
            reminder = FollowUpReminder(
                contact_id=contact_id,
                contact_name=contact.name,
                due_date=follow_up_date.isoformat(),
                reason=interaction.next_action,
                priority=3
            )
            self.follow_up_reminders.append(reminder)
    
    async def search_contacts(self, query: str) -> List[Contact]:
        """Поиск контактов"""
        try:
            results = []
            query_lower = query.lower()
            
            for contact in self.contacts.values():
                # Поиск по имени, компании, позиции
                if (query_lower in contact.name.lower() or
                    (contact.company and query_lower in contact.company.lower()) or
                    (contact.position and query_lower in contact.position.lower()) or
                    any(query_lower in tag.lower() for tag in contact.tags)):
                    results.append(contact)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Ошибка поиска контактов: {e}")
            return []
    
    async def get_contacts_by_status(self, status: ContactStatus) -> List[Contact]:
        """Получение контактов по статусу"""
        return [contact for contact in self.contacts.values() if contact.status == status]
    
    async def get_follow_up_reminders(self) -> List[FollowUpReminder]:
        """Получение напоминаний о follow-up"""
        today = datetime.now()
        
        reminders = []
        for reminder in self.follow_up_reminders:
            if not reminder.completed:
                due_date = datetime.fromisoformat(reminder.due_date)
                if due_date <= today:
                    reminders.append(reminder)
        
        return sorted(reminders, key=lambda x: x.priority, reverse=True)
    
    async def get_contact_timeline(self, contact_id: str) -> List[Interaction]:
        """Получение временной линии контакта"""
        if contact_id not in self.interactions:
            return []
        
        return sorted(self.interactions[contact_id], key=lambda x: x.date, reverse=True)
    
    async def get_network_insights(self) -> Dict[str, Any]:
        """Получение инсайтов о сети"""
        try:
            total_contacts = len(self.contacts)
            
            # Статистика по статусам
            status_stats = {}
            for contact in self.contacts.values():
                status = contact.status.value
                status_stats[status] = status_stats.get(status, 0) + 1
            
            # Статистика по компаниям
            company_stats = {}
            for contact in self.contacts.values():
                if contact.company:
                    company_stats[contact.company] = company_stats.get(contact.company, 0) + 1
            
            # Активность за последний месяц
            month_ago = datetime.now() - timedelta(days=30)
            recent_interactions = 0
            for interactions in self.interactions.values():
                for interaction in interactions:
                    if datetime.fromisoformat(interaction.date) >= month_ago:
                        recent_interactions += 1
            
            return {
                'total_contacts': total_contacts,
                'status_distribution': status_stats,
                'top_companies': dict(sorted(company_stats.items(), key=lambda x: x[1], reverse=True)[:5]),
                'recent_interactions': recent_interactions,
                'pending_follow_ups': len([r for r in self.follow_up_reminders if not r.completed])
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка получения инсайтов: {e}")
            return {}
    
    async def suggest_follow_up(self, contact_id: str) -> Optional[str]:
        """Предложение follow-up"""
        try:
            if contact_id not in self.contacts:
                return None
            
            contact = self.contacts[contact_id]
            timeline = await self.get_contact_timeline(contact_id)
            
            if not timeline:
                return "Отправьте первое сообщение"
            
            last_interaction = timeline[0]
            
            # Анализируем последнее взаимодействие
            if last_interaction.type == InteractionType.EMAIL:
                if "встреча" in last_interaction.content.lower():
                    return "Назначьте встречу"
                elif "резюме" in last_interaction.content.lower():
                    return "Отправьте резюме"
                else:
                    return "Отправьте follow-up сообщение"
            
            elif last_interaction.type == InteractionType.MEETING:
                return "Отправьте благодарность за встречу"
            
            elif last_interaction.type == InteractionType.PHONE:
                return "Отправьте резюме по email"
            
            return "Проверьте статус заявки"
            
        except Exception as e:
            self.logger.error(f"Ошибка предложения follow-up: {e}")
            return None
    
    def format_contact_card(self, contact: Contact) -> str:
        """Форматирование карточки контакта"""
        text = f"👤 <b>{contact.name}</b>\n"
        
        if contact.position and contact.company:
            text += f"💼 {contact.position} в {contact.company}\n"
        elif contact.company:
            text += f"🏢 {contact.company}\n"
        
        if contact.email:
            text += f"📧 {contact.email}\n"
        
        if contact.phone:
            text += f"📞 {contact.phone}\n"
        
        if contact.linkedin:
            text += f"🔗 LinkedIn: {contact.linkedin}\n"
        
        text += f"🏷️ Статус: {contact.status.value}\n"
        
        if contact.tags:
            text += f"🏷️ Теги: {', '.join(contact.tags)}\n"
        
        if contact.last_contact:
            last_contact_date = datetime.fromisoformat(contact.last_contact).strftime('%d.%m.%Y')
            text += f"📅 Последний контакт: {last_contact_date}\n"
        
        if contact.notes:
            text += f"📝 Заметки: {contact.notes}\n"
        
        return text
    
    def format_network_insights(self, insights: Dict[str, Any]) -> str:
        """Форматирование инсайтов сети"""
        text = f"📊 <b>Инсайты сети</b>\n\n"
        
        text += f"👥 Всего контактов: {insights.get('total_contacts', 0)}\n"
        text += f"📈 Взаимодействий за месяц: {insights.get('recent_interactions', 0)}\n"
        text += f"⏰ Ожидают follow-up: {insights.get('pending_follow_ups', 0)}\n\n"
        
        if insights.get('status_distribution'):
            text += f"📊 <b>Статусы:</b>\n"
            for status, count in insights['status_distribution'].items():
                text += f"• {status}: {count}\n"
            text += "\n"
        
        if insights.get('top_companies'):
            text += f"🏢 <b>Топ компании:</b>\n"
            for company, count in insights['top_companies'].items():
                text += f"• {company}: {count}\n"
        
        return text


# Функция для тестирования
async def test_personal_crm():
    """Тестирование личного CRM"""
    crm = PersonalCRM()
    
    # Добавляем контакт
    contact_data = {
        'name': 'Иван Петров',
        'email': 'ivan@company.com',
        'company': 'Tech Corp',
        'position': 'HR Manager',
        'linkedin': 'https://linkedin.com/in/ivanpetrov',
        'tags': ['hr', 'tech'],
        'source': 'linkedin'
    }
    
    contact_id = await crm.add_contact(contact_data)
    print(f"Добавлен контакт: {contact_id}")
    
    # Добавляем взаимодействие
    interaction_data = {
        'type': 'email',
        'content': 'Отправил резюме на позицию Python разработчика',
        'outcome': 'Получен ответ с приглашением на собеседование',
        'next_action': 'Подготовиться к техническому интервью'
    }
    
    interaction_id = await crm.add_interaction(contact_id, interaction_data)
    print(f"Добавлено взаимодействие: {interaction_id}")
    
    # Получаем инсайты
    insights = await crm.get_network_insights()
    print("\nИнсайты сети:")
    print(crm.format_network_insights(insights))
    
    # Предложение follow-up
    suggestion = await crm.suggest_follow_up(contact_id)
    print(f"\nПредложение follow-up: {suggestion}")


if __name__ == "__main__":
    asyncio.run(test_personal_crm())
