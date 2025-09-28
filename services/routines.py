# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Планировщик повторяющихся рутин и напоминаний
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class RoutineType(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class RoutineStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class Routine:
    id: str
    title: str
    description: str
    routine_type: RoutineType
    frequency: int  # для custom типа
    days_of_week: List[int]  # 0-6, где 0 = понедельник
    time: str  # HH:MM
    reminder_minutes: int  # за сколько минут напомнить
    status: RoutineStatus
    created_at: datetime
    last_completed: Optional[datetime] = None
    completion_count: int = 0
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class Reminder:
    id: str
    routine_id: str
    title: str
    message: str
    scheduled_time: datetime
    status: str  # pending, sent, cancelled
    created_at: datetime

class RoutinesService:
    """Сервис планировщика рутин и напоминаний"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.routines_file = self.storage_dir / "routines.json"
        self.reminders_file = self.storage_dir / "reminders.json"
        
        # Загружаем данные
        self.routines = self._load_routines()
        self.reminders = self._load_reminders()
    
    def _load_routines(self) -> Dict[str, Routine]:
        """Загрузка рутин из файла"""
        try:
            if self.routines_file.exists():
                with open(self.routines_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    routines = {}
                    for routine_id, routine_data in data.items():
                        routine_data['routine_type'] = RoutineType(routine_data['routine_type'])
                        routine_data['status'] = RoutineStatus(routine_data['status'])
                        routine_data['created_at'] = datetime.fromisoformat(routine_data['created_at'])
                        if routine_data.get('last_completed'):
                            routine_data['last_completed'] = datetime.fromisoformat(routine_data['last_completed'])
                        routines[routine_id] = Routine(**routine_data)
                    return routines
        except Exception as e:
            print(f"Ошибка загрузки рутин: {e}")
        return {}
    
    def _save_routines(self):
        """Сохранение рутин в файл"""
        try:
            data = {}
            for routine_id, routine in self.routines.items():
                routine_dict = asdict(routine)
                routine_dict['routine_type'] = routine.routine_type.value
                routine_dict['status'] = routine.status.value
                routine_dict['created_at'] = routine.created_at.isoformat()
                if routine.last_completed:
                    routine_dict['last_completed'] = routine.last_completed.isoformat()
                data[routine_id] = routine_dict
            
            with open(self.routines_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения рутин: {e}")
    
    def _load_reminders(self) -> Dict[str, Reminder]:
        """Загрузка напоминаний из файла"""
        try:
            if self.reminders_file.exists():
                with open(self.reminders_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    reminders = {}
                    for reminder_id, reminder_data in data.items():
                        reminder_data['scheduled_time'] = datetime.fromisoformat(reminder_data['scheduled_time'])
                        reminder_data['created_at'] = datetime.fromisoformat(reminder_data['created_at'])
                        reminders[reminder_id] = Reminder(**reminder_data)
                    return reminders
        except Exception as e:
            print(f"Ошибка загрузки напоминаний: {e}")
        return {}
    
    def _save_reminders(self):
        """Сохранение напоминаний в файл"""
        try:
            data = {}
            for reminder_id, reminder in self.reminders.items():
                reminder_dict = asdict(reminder)
                reminder_dict['scheduled_time'] = reminder.scheduled_time.isoformat()
                reminder_dict['created_at'] = reminder.created_at.isoformat()
                data[reminder_id] = reminder_dict
            
            with open(self.reminders_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения напоминаний: {e}")
    
    def add_routine(self, title: str, description: str, routine_type: RoutineType, 
                   time: str, reminder_minutes: int = 15, frequency: int = 1,
                   days_of_week: List[int] = None, tags: List[str] = None) -> str:
        """Добавление новой рутины"""
        try:
            routine_id = str(uuid.uuid4())
            
            if days_of_week is None:
                if routine_type == RoutineType.DAILY:
                    days_of_week = list(range(7))  # все дни
                elif routine_type == RoutineType.WEEKLY:
                    days_of_week = [0]  # понедельник
                elif routine_type == RoutineType.MONTHLY:
                    days_of_week = [0]  # первый понедельник месяца
                else:
                    days_of_week = [0]  # по умолчанию понедельник
            
            routine = Routine(
                id=routine_id,
                title=title,
                description=description,
                routine_type=routine_type,
                frequency=frequency,
                days_of_week=days_of_week,
                time=time,
                reminder_minutes=reminder_minutes,
                status=RoutineStatus.ACTIVE,
                created_at=datetime.now(),
                tags=tags or []
            )
            
            self.routines[routine_id] = routine
            self._save_routines()
            
            # Создаем напоминания
            self._create_reminders_for_routine(routine)
            
            return routine_id
            
        except Exception as e:
            print(f"Ошибка добавления рутины: {e}")
            return None
    
    def _create_reminders_for_routine(self, routine: Routine):
        """Создание напоминаний для рутины"""
        try:
            now = datetime.now()
            current_time = now.time()
            routine_time = datetime.strptime(routine.time, "%H:%M").time()
            
            # Создаем напоминания на следующие 30 дней
            for i in range(30):
                reminder_date = now + timedelta(days=i)
                
                # Проверяем, подходит ли день недели
                if routine.routine_type == RoutineType.DAILY or routine.routine_type == RoutineType.CUSTOM:
                    if reminder_date.weekday() in routine.days_of_week:
                        self._create_reminder(routine, reminder_date)
                elif routine.routine_type == RoutineType.WEEKLY:
                    if reminder_date.weekday() in routine.days_of_week:
                        self._create_reminder(routine, reminder_date)
                elif routine.routine_type == RoutineType.MONTHLY:
                    if reminder_date.day == 1 and reminder_date.weekday() in routine.days_of_week:
                        self._create_reminder(routine, reminder_date)
                        
        except Exception as e:
            print(f"Ошибка создания напоминаний: {e}")
    
    def _create_reminder(self, routine: Routine, reminder_date: datetime):
        """Создание напоминания"""
        try:
            reminder_id = str(uuid.uuid4())
            scheduled_time = datetime.combine(reminder_date.date(), datetime.strptime(routine.time, "%H:%M").time())
            scheduled_time -= timedelta(minutes=routine.reminder_minutes)
            
            reminder = Reminder(
                id=reminder_id,
                routine_id=routine.id,
                title=f"Напоминание: {routine.title}",
                message=f"Через {routine.reminder_minutes} минут: {routine.description}",
                scheduled_time=scheduled_time,
                status="pending",
                created_at=datetime.now()
            )
            
            self.reminders[reminder_id] = reminder
            self._save_reminders()
            
        except Exception as e:
            print(f"Ошибка создания напоминания: {e}")
    
    def get_routines(self, status: RoutineStatus = None) -> List[Routine]:
        """Получение списка рутин"""
        try:
            routines = list(self.routines.values())
            if status:
                routines = [r for r in routines if r.status == status]
            return sorted(routines, key=lambda x: x.created_at, reverse=True)
        except Exception as e:
            print(f"Ошибка получения рутин: {e}")
            return []
    
    def get_routine(self, routine_id: str) -> Optional[Routine]:
        """Получение рутины по ID"""
        return self.routines.get(routine_id)
    
    def update_routine_status(self, routine_id: str, status: RoutineStatus):
        """Обновление статуса рутины"""
        try:
            if routine_id in self.routines:
                self.routines[routine_id].status = status
                self._save_routines()
                return True
        except Exception as e:
            print(f"Ошибка обновления статуса рутины: {e}")
        return False
    
    def complete_routine(self, routine_id: str):
        """Отметка рутины как выполненной"""
        try:
            if routine_id in self.routines:
                routine = self.routines[routine_id]
                routine.last_completed = datetime.now()
                routine.completion_count += 1
                self._save_routines()
                return True
        except Exception as e:
            print(f"Ошибка отметки выполнения рутины: {e}")
        return False
    
    def get_pending_reminders(self) -> List[Reminder]:
        """Получение ожидающих напоминаний"""
        try:
            now = datetime.now()
            pending = []
            for reminder in self.reminders.values():
                if reminder.status == "pending" and reminder.scheduled_time <= now:
                    pending.append(reminder)
            return sorted(pending, key=lambda x: x.scheduled_time)
        except Exception as e:
            print(f"Ошибка получения напоминаний: {e}")
            return []
    
    def mark_reminder_sent(self, reminder_id: str):
        """Отметка напоминания как отправленного"""
        try:
            if reminder_id in self.reminders:
                self.reminders[reminder_id].status = "sent"
                self._save_reminders()
                return True
        except Exception as e:
            print(f"Ошибка отметки напоминания: {e}")
        return False
    
    def get_routine_stats(self, routine_id: str) -> Dict[str, Any]:
        """Получение статистики рутины"""
        try:
            routine = self.get_routine(routine_id)
            if not routine:
                return {}
            
            # Подсчитываем выполненные напоминания
            completed_reminders = sum(1 for r in self.reminders.values() 
                                    if r.routine_id == routine_id and r.status == "sent")
            
            # Подсчитываем пропущенные напоминания
            missed_reminders = sum(1 for r in self.reminders.values() 
                                 if r.routine_id == routine_id and r.status == "pending" 
                                 and r.scheduled_time < datetime.now())
            
            return {
                "routine_id": routine_id,
                "title": routine.title,
                "completion_count": routine.completion_count,
                "completed_reminders": completed_reminders,
                "missed_reminders": missed_reminders,
                "completion_rate": completed_reminders / max(1, completed_reminders + missed_reminders),
                "last_completed": routine.last_completed.isoformat() if routine.last_completed else None,
                "status": routine.status.value
            }
        except Exception as e:
            print(f"Ошибка получения статистики рутины: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        try:
            total_routines = len(self.routines)
            active_routines = len([r for r in self.routines.values() if r.status == RoutineStatus.ACTIVE])
            total_reminders = len(self.reminders)
            pending_reminders = len([r for r in self.reminders.values() if r.status == "pending"])
            
            return {
                "total_routines": total_routines,
                "active_routines": active_routines,
                "total_reminders": total_reminders,
                "pending_reminders": pending_reminders,
                "completion_rate": sum(r.completion_count for r in self.routines.values()) / max(1, total_reminders)
            }
        except Exception as e:
            print(f"Ошибка получения общей статистики: {e}")
            return {}
    
    def export_routines(self, format: str = "json") -> str:
        """Экспорт рутин"""
        try:
            if format == "json":
                return json.dumps({r.id: asdict(r) for r in self.routines.values()}, 
                                 ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["ID", "Title", "Type", "Time", "Status", "Completions", "Last Completed"])
                for routine in self.routines.values():
                    writer.writerow([
                        routine.id,
                        routine.title,
                        routine.routine_type.value,
                        routine.time,
                        routine.status.value,
                        routine.completion_count,
                        routine.last_completed.isoformat() if routine.last_completed else ""
                    ])
                return output.getvalue()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта рутин: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = RoutinesService()
    
    # Добавляем тестовую рутину
    routine_id = service.add_routine(
        title="Утренняя зарядка",
        description="15 минут упражнений",
        routine_type=RoutineType.DAILY,
        time="07:00",
        reminder_minutes=10,
        tags=["здоровье", "утро"]
    )
    
    print(f"Добавлена рутина: {routine_id}")
    print(f"Статистика: {service.get_all_stats()}")
    print(f"Ожидающие напоминания: {len(service.get_pending_reminders())}")
