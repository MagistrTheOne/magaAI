# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Мини-CRM: контакты, дни рождения, follow-up
"""

import json
import os
import re
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class ContactType(Enum):
    PERSONAL = "personal"
    PROFESSIONAL = "professional"
    BUSINESS = "business"
    FAMILY = "family"
    FRIEND = "friend"
    COLLEAGUE = "colleague"
    CLIENT = "client"
    VENDOR = "vendor"

class InteractionType(Enum):
    EMAIL = "email"
    PHONE = "phone"
    MEETING = "meeting"
    MESSAGE = "message"
    SOCIAL = "social"
    OTHER = "other"

class FollowUpStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"

@dataclass
class Contact:
    id: str
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    contact_type: ContactType = ContactType.PERSONAL
    birthday: Optional[date] = None
    address: Optional[str] = None
    notes: str = ""
    tags: List[str] = None
    created_at: datetime = None
    updated_at: datetime = None
    last_contact: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.tags is None:
            self.tags = []
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

@dataclass
class Interaction:
    id: str
    contact_id: str
    interaction_type: InteractionType
    subject: str
    content: str
    interaction_date: datetime
    duration: Optional[int] = None  # в минутах
    notes: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class FollowUp:
    id: str
    contact_id: str
    title: str
    description: str
    due_date: datetime
    status: FollowUpStatus = FollowUpStatus.PENDING
    priority: int = 3  # 1-5, где 5 - высший приоритет
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    notes: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.tags is None:
            self.tags = []

class PersonalCRMService:
    """Сервис персонального CRM"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.contacts_file = self.storage_dir / "contacts.json"
        self.interactions_file = self.storage_dir / "interactions.json"
        self.followups_file = self.storage_dir / "followups.json"
        
        # Загружаем данные
        self.contacts = self._load_contacts()
        self.interactions = self._load_interactions()
        self.followups = self._load_followups()
    
    def _load_contacts(self) -> Dict[str, Contact]:
        """Загрузка контактов из файла"""
        try:
            if self.contacts_file.exists():
                with open(self.contacts_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    contacts = {}
                    for contact_id, contact_data in data.items():
                        contact_data['contact_type'] = ContactType(contact_data['contact_type'])
                        if contact_data.get('birthday'):
                            contact_data['birthday'] = date.fromisoformat(contact_data['birthday'])
                        contact_data['created_at'] = datetime.fromisoformat(contact_data['created_at'])
                        contact_data['updated_at'] = datetime.fromisoformat(contact_data['updated_at'])
                        if contact_data.get('last_contact'):
                            contact_data['last_contact'] = datetime.fromisoformat(contact_data['last_contact'])
                        contacts[contact_id] = Contact(**contact_data)
                    return contacts
        except Exception as e:
            print(f"Ошибка загрузки контактов: {e}")
        return {}
    
    def _save_contacts(self):
        """Сохранение контактов в файл"""
        try:
            data = {}
            for contact_id, contact in self.contacts.items():
                contact_dict = asdict(contact)
                contact_dict['contact_type'] = contact.contact_type.value
                if contact.birthday:
                    contact_dict['birthday'] = contact.birthday.isoformat()
                contact_dict['created_at'] = contact.created_at.isoformat()
                contact_dict['updated_at'] = contact.updated_at.isoformat()
                if contact.last_contact:
                    contact_dict['last_contact'] = contact.last_contact.isoformat()
                data[contact_id] = contact_dict
            
            with open(self.contacts_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения контактов: {e}")
    
    def _load_interactions(self) -> Dict[str, Interaction]:
        """Загрузка взаимодействий из файла"""
        try:
            if self.interactions_file.exists():
                with open(self.interactions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    interactions = {}
                    for interaction_id, interaction_data in data.items():
                        interaction_data['interaction_type'] = InteractionType(interaction_data['interaction_type'])
                        interaction_data['interaction_date'] = datetime.fromisoformat(interaction_data['interaction_date'])
                        interactions[interaction_id] = Interaction(**interaction_data)
                    return interactions
        except Exception as e:
            print(f"Ошибка загрузки взаимодействий: {e}")
        return {}
    
    def _save_interactions(self):
        """Сохранение взаимодействий в файл"""
        try:
            data = {}
            for interaction_id, interaction in self.interactions.items():
                interaction_dict = asdict(interaction)
                interaction_dict['interaction_type'] = interaction.interaction_type.value
                interaction_dict['interaction_date'] = interaction.interaction_date.isoformat()
                data[interaction_id] = interaction_dict
            
            with open(self.interactions_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения взаимодействий: {e}")
    
    def _load_followups(self) -> Dict[str, FollowUp]:
        """Загрузка follow-up из файла"""
        try:
            if self.followups_file.exists():
                with open(self.followups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    followups = {}
                    for followup_id, followup_data in data.items():
                        followup_data['status'] = FollowUpStatus(followup_data['status'])
                        followup_data['due_date'] = datetime.fromisoformat(followup_data['due_date'])
                        followup_data['created_at'] = datetime.fromisoformat(followup_data['created_at'])
                        if followup_data.get('completed_at'):
                            followup_data['completed_at'] = datetime.fromisoformat(followup_data['completed_at'])
                        followups[followup_id] = FollowUp(**followup_data)
                    return followups
        except Exception as e:
            print(f"Ошибка загрузки follow-up: {e}")
        return {}
    
    def _save_followups(self):
        """Сохранение follow-up в файл"""
        try:
            data = {}
            for followup_id, followup in self.followups.items():
                followup_dict = asdict(followup)
                followup_dict['status'] = followup.status.value
                followup_dict['due_date'] = followup.due_date.isoformat()
                followup_dict['created_at'] = followup.created_at.isoformat()
                if followup.completed_at:
                    followup_dict['completed_at'] = followup.completed_at.isoformat()
                data[followup_id] = followup_dict
            
            with open(self.followups_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения follow-up: {e}")
    
    def add_contact(self, first_name: str, last_name: str, email: str = None,
                   phone: str = None, company: str = None, position: str = None,
                   contact_type: ContactType = ContactType.PERSONAL,
                   birthday: date = None, address: str = None,
                   notes: str = "", tags: List[str] = None) -> str:
        """Добавление нового контакта"""
        try:
            contact_id = str(uuid.uuid4())
            
            contact = Contact(
                id=contact_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                company=company,
                position=position,
                contact_type=contact_type,
                birthday=birthday,
                address=address,
                notes=notes,
                tags=tags or []
            )
            
            self.contacts[contact_id] = contact
            self._save_contacts()
            
            return contact_id
            
        except Exception as e:
            print(f"Ошибка добавления контакта: {e}")
            return None
    
    def add_interaction(self, contact_id: str, interaction_type: InteractionType,
                       subject: str, content: str, interaction_date: datetime = None,
                       duration: int = None, notes: str = "", tags: List[str] = None) -> str:
        """Добавление взаимодействия"""
        try:
            if contact_id not in self.contacts:
                return None
            
            interaction_id = str(uuid.uuid4())
            
            if interaction_date is None:
                interaction_date = datetime.now()
            
            interaction = Interaction(
                id=interaction_id,
                contact_id=contact_id,
                interaction_type=interaction_type,
                subject=subject,
                content=content,
                interaction_date=interaction_date,
                duration=duration,
                notes=notes,
                tags=tags or []
            )
            
            self.interactions[interaction_id] = interaction
            
            # Обновляем последний контакт
            self.contacts[contact_id].last_contact = interaction_date
            self.contacts[contact_id].updated_at = datetime.now()
            
            self._save_interactions()
            self._save_contacts()
            
            return interaction_id
            
        except Exception as e:
            print(f"Ошибка добавления взаимодействия: {e}")
            return None
    
    def add_followup(self, contact_id: str, title: str, description: str,
                    due_date: datetime, priority: int = 3,
                    notes: str = "", tags: List[str] = None) -> str:
        """Добавление follow-up"""
        try:
            if contact_id not in self.contacts:
                return None
            
            followup_id = str(uuid.uuid4())
            
            followup = FollowUp(
                id=followup_id,
                contact_id=contact_id,
                title=title,
                description=description,
                due_date=due_date,
                priority=priority,
                notes=notes,
                tags=tags or []
            )
            
            self.followups[followup_id] = followup
            self._save_followups()
            
            return followup_id
            
        except Exception as e:
            print(f"Ошибка добавления follow-up: {e}")
            return None
    
    def get_contacts(self, contact_type: ContactType = None) -> List[Contact]:
        """Получение списка контактов"""
        try:
            contacts = list(self.contacts.values())
            if contact_type:
                contacts = [c for c in contacts if c.contact_type == contact_type]
            return sorted(contacts, key=lambda x: x.full_name)
        except Exception as e:
            print(f"Ошибка получения контактов: {e}")
            return []
    
    def get_contact(self, contact_id: str) -> Optional[Contact]:
        """Получение контакта по ID"""
        return self.contacts.get(contact_id)
    
    def search_contacts(self, query: str) -> List[Contact]:
        """Поиск контактов"""
        try:
            query_lower = query.lower()
            results = []
            
            for contact in self.contacts.values():
                if (query_lower in contact.first_name.lower() or
                    query_lower in contact.last_name.lower() or
                    query_lower in contact.full_name.lower() or
                    (contact.email and query_lower in contact.email.lower()) or
                    (contact.company and query_lower in contact.company.lower()) or
                    (contact.position and query_lower in contact.position.lower())):
                    results.append(contact)
            
            return sorted(results, key=lambda x: x.full_name)
        except Exception as e:
            print(f"Ошибка поиска контактов: {e}")
            return []
    
    def get_contact_interactions(self, contact_id: str) -> List[Interaction]:
        """Получение взаимодействий контакта"""
        try:
            interactions = [i for i in self.interactions.values() if i.contact_id == contact_id]
            return sorted(interactions, key=lambda x: x.interaction_date, reverse=True)
        except Exception as e:
            print(f"Ошибка получения взаимодействий контакта: {e}")
            return []
    
    def get_contact_followups(self, contact_id: str, status: FollowUpStatus = None) -> List[FollowUp]:
        """Получение follow-up контакта"""
        try:
            followups = [f for f in self.followups.values() if f.contact_id == contact_id]
            if status:
                followups = [f for f in followups if f.status == status]
            return sorted(followups, key=lambda x: x.due_date)
        except Exception as e:
            print(f"Ошибка получения follow-up контакта: {e}")
            return []
    
    def get_upcoming_birthdays(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Получение предстоящих дней рождения"""
        try:
            now = date.today()
            upcoming = []
            
            for contact in self.contacts.values():
                if contact.birthday:
                    # Создаем дату дня рождения в текущем году
                    this_year_birthday = contact.birthday.replace(year=now.year)
                    
                    # Если день рождения уже прошел в этом году, берем следующий год
                    if this_year_birthday < now:
                        this_year_birthday = contact.birthday.replace(year=now.year + 1)
                    
                    days_until = (this_year_birthday - now).days
                    if days_until <= days_ahead:
                        upcoming.append({
                            'contact_id': contact.id,
                            'name': contact.full_name,
                            'birthday': this_year_birthday,
                            'days_until': days_until,
                            'age': this_year_birthday.year - contact.birthday.year
                        })
            
            return sorted(upcoming, key=lambda x: x['days_until'])
        except Exception as e:
            print(f"Ошибка получения предстоящих дней рождения: {e}")
            return []
    
    def get_due_followups(self, days_ahead: int = 7) -> List[FollowUp]:
        """Получение предстоящих follow-up"""
        try:
            now = datetime.now()
            end_date = now + timedelta(days=days_ahead)
            
            due_followups = []
            for followup in self.followups.values():
                if (followup.status == FollowUpStatus.PENDING and 
                    followup.due_date <= end_date):
                    due_followups.append(followup)
            
            return sorted(due_followups, key=lambda x: x.due_date)
        except Exception as e:
            print(f"Ошибка получения предстоящих follow-up: {e}")
            return []
    
    def complete_followup(self, followup_id: str, notes: str = "") -> bool:
        """Завершение follow-up"""
        try:
            if followup_id not in self.followups:
                return False
            
            followup = self.followups[followup_id]
            followup.status = FollowUpStatus.COMPLETED
            followup.completed_at = datetime.now()
            if notes:
                followup.notes = notes
            
            self._save_followups()
            return True
            
        except Exception as e:
            print(f"Ошибка завершения follow-up: {e}")
            return False
    
    def get_contact_stats(self, contact_id: str) -> Dict[str, Any]:
        """Получение статистики контакта"""
        try:
            contact = self.get_contact(contact_id)
            if not contact:
                return {}
            
            interactions = self.get_contact_interactions(contact_id)
            followups = self.get_contact_followups(contact_id)
            
            # Статистика по типам взаимодействий
            interaction_types = {}
            for interaction in interactions:
                interaction_type = interaction.interaction_type.value
                if interaction_type not in interaction_types:
                    interaction_types[interaction_type] = 0
                interaction_types[interaction_type] += 1
            
            # Статистика follow-up
            pending_followups = len([f for f in followups if f.status == FollowUpStatus.PENDING])
            completed_followups = len([f for f in followups if f.status == FollowUpStatus.COMPLETED])
            
            return {
                'contact_id': contact_id,
                'name': contact.full_name,
                'contact_type': contact.contact_type.value,
                'total_interactions': len(interactions),
                'interaction_types': interaction_types,
                'last_interaction': max(interactions, key=lambda x: x.interaction_date).interaction_date.isoformat() if interactions else None,
                'total_followups': len(followups),
                'pending_followups': pending_followups,
                'completed_followups': completed_followups,
                'followup_completion_rate': completed_followups / max(1, len(followups))
            }
        except Exception as e:
            print(f"Ошибка получения статистики контакта: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        try:
            total_contacts = len(self.contacts)
            total_interactions = len(self.interactions)
            total_followups = len(self.followups)
            pending_followups = len([f for f in self.followups.values() if f.status == FollowUpStatus.PENDING])
            
            # Статистика по типам контактов
            by_type = {}
            for contact in self.contacts.values():
                contact_type = contact.contact_type.value
                if contact_type not in by_type:
                    by_type[contact_type] = 0
                by_type[contact_type] += 1
            
            # Статистика по типам взаимодействий
            interaction_types = {}
            for interaction in self.interactions.values():
                interaction_type = interaction.interaction_type.value
                if interaction_type not in interaction_types:
                    interaction_types[interaction_type] = 0
                interaction_types[interaction_type] += 1
            
            return {
                'total_contacts': total_contacts,
                'total_interactions': total_interactions,
                'total_followups': total_followups,
                'pending_followups': pending_followups,
                'by_contact_type': by_type,
                'by_interaction_type': interaction_types
            }
        except Exception as e:
            print(f"Ошибка получения общей статистики: {e}")
            return {}
    
    def export_contacts(self, format: str = "json") -> str:
        """Экспорт контактов"""
        try:
            if format == "json":
                return json.dumps({c.id: asdict(c) for c in self.contacts.values()}, 
                                 ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Name", "Email", "Phone", "Company", "Type", "Birthday"])
                for contact in self.contacts.values():
                    writer.writerow([
                        contact.full_name,
                        contact.email or "",
                        contact.phone or "",
                        contact.company or "",
                        contact.contact_type.value,
                        contact.birthday.isoformat() if contact.birthday else ""
                    ])
                return output.getvalue()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта контактов: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = PersonalCRMService()
    
    # Добавляем тестовый контакт
    contact_id = service.add_contact(
        first_name="Иван",
        last_name="Петров",
        email="ivan@example.com",
        phone="+7-123-456-7890",
        company="ООО Ромашка",
        position="Менеджер",
        contact_type=ContactType.PROFESSIONAL,
        birthday=date(1990, 5, 15)
    )
    
    # Добавляем взаимодействие
    interaction_id = service.add_interaction(
        contact_id=contact_id,
        interaction_type=InteractionType.EMAIL,
        subject="Встреча",
        content="Обсуждение проекта"
    )
    
    # Добавляем follow-up
    followup_id = service.add_followup(
        contact_id=contact_id,
        title="Отправить предложение",
        description="Подготовить коммерческое предложение",
        due_date=datetime.now() + timedelta(days=3)
    )
    
    print(f"Добавлен контакт: {contact_id}")
    print(f"Добавлено взаимодействие: {interaction_id}")
    print(f"Добавлен follow-up: {followup_id}")
    print(f"Статистика: {service.get_all_stats()}")
