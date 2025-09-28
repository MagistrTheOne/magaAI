# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Ежедневный фокус-план (3 приоритета)
"""

import json
import os
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class PriorityLevel(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class FocusTask:
    id: str
    title: str
    description: str
    priority: PriorityLevel
    status: TaskStatus
    created_at: datetime
    due_date: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # в минутах
    actual_duration: Optional[int] = None  # в минутах
    completed_at: Optional[datetime] = None
    tags: List[str] = None
    notes: str = ""
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

@dataclass
class DailyFocus:
    id: str
    date: date
    focus_tasks: List[str]  # IDs of tasks
    morning_energy: int = 5  # 1-10
    evening_energy: int = 5  # 1-10
    distractions: List[str] = None
    achievements: List[str] = None
    reflection: str = ""
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.distractions is None:
            self.distractions = []
        if self.achievements is None:
            self.achievements = []

class DailyFocusService:
    """Сервис ежедневного фокуса"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.tasks_file = self.storage_dir / "focus_tasks.json"
        self.daily_focus_file = self.storage_dir / "daily_focus.json"
        
        # Загружаем данные
        self.tasks = self._load_tasks()
        self.daily_focus = self._load_daily_focus()
    
    def _load_tasks(self) -> Dict[str, FocusTask]:
        """Загрузка задач из файла"""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    tasks = {}
                    for task_id, task_data in data.items():
                        task_data['priority'] = PriorityLevel(task_data['priority'])
                        task_data['status'] = TaskStatus(task_data['status'])
                        task_data['created_at'] = datetime.fromisoformat(task_data['created_at'])
                        if task_data.get('due_date'):
                            task_data['due_date'] = datetime.fromisoformat(task_data['due_date'])
                        if task_data.get('completed_at'):
                            task_data['completed_at'] = datetime.fromisoformat(task_data['completed_at'])
                        tasks[task_id] = FocusTask(**task_data)
                    return tasks
        except Exception as e:
            print(f"Ошибка загрузки задач: {e}")
        return {}
    
    def _save_tasks(self):
        """Сохранение задач в файл"""
        try:
            data = {}
            for task_id, task in self.tasks.items():
                task_dict = asdict(task)
                task_dict['priority'] = task.priority.value
                task_dict['status'] = task.status.value
                task_dict['created_at'] = task.created_at.isoformat()
                if task.due_date:
                    task_dict['due_date'] = task.due_date.isoformat()
                if task.completed_at:
                    task_dict['completed_at'] = task.completed_at.isoformat()
                data[task_id] = task_dict
            
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения задач: {e}")
    
    def _load_daily_focus(self) -> Dict[str, DailyFocus]:
        """Загрузка ежедневного фокуса из файла"""
        try:
            if self.daily_focus_file.exists():
                with open(self.daily_focus_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    daily_focus = {}
                    for focus_id, focus_data in data.items():
                        focus_data['date'] = date.fromisoformat(focus_data['date'])
                        focus_data['created_at'] = datetime.fromisoformat(focus_data['created_at'])
                        daily_focus[focus_id] = DailyFocus(**focus_data)
                    return daily_focus
        except Exception as e:
            print(f"Ошибка загрузки ежедневного фокуса: {e}")
        return {}
    
    def _save_daily_focus(self):
        """Сохранение ежедневного фокуса в файл"""
        try:
            data = {}
            for focus_id, focus in self.daily_focus.items():
                focus_dict = asdict(focus)
                focus_dict['date'] = focus.date.isoformat()
                focus_dict['created_at'] = focus.created_at.isoformat()
                data[focus_id] = focus_dict
            
            with open(self.daily_focus_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения ежедневного фокуса: {e}")
    
    def add_task(self, title: str, description: str, priority: PriorityLevel,
                 due_date: Optional[datetime] = None, estimated_duration: Optional[int] = None,
                 tags: List[str] = None, notes: str = "") -> str:
        """Добавление новой задачи"""
        try:
            task_id = str(uuid.uuid4())
            
            task = FocusTask(
                id=task_id,
                title=title,
                description=description,
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=datetime.now(),
                due_date=due_date,
                estimated_duration=estimated_duration,
                tags=tags or [],
                notes=notes
            )
            
            self.tasks[task_id] = task
            self._save_tasks()
            
            return task_id
            
        except Exception as e:
            print(f"Ошибка добавления задачи: {e}")
            return None
    
    def create_daily_focus(self, focus_date: date, task_ids: List[str], 
                          morning_energy: int = 5, evening_energy: int = 5) -> str:
        """Создание ежедневного фокуса"""
        try:
            focus_id = str(uuid.uuid4())
            
            # Проверяем, что задачи существуют
            valid_task_ids = [tid for tid in task_ids if tid in self.tasks]
            
            focus = DailyFocus(
                id=focus_id,
                date=focus_date,
                focus_tasks=valid_task_ids,
                morning_energy=morning_energy,
                evening_energy=evening_energy
            )
            
            self.daily_focus[focus_id] = focus
            self._save_daily_focus()
            
            return focus_id
            
        except Exception as e:
            print(f"Ошибка создания ежедневного фокуса: {e}")
            return None
    
    def get_tasks(self, status: TaskStatus = None, priority: PriorityLevel = None) -> List[FocusTask]:
        """Получение списка задач"""
        try:
            tasks = list(self.tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            return sorted(tasks, key=lambda x: x.created_at, reverse=True)
        except Exception as e:
            print(f"Ошибка получения задач: {e}")
            return []
    
    def get_task(self, task_id: str) -> Optional[FocusTask]:
        """Получение задачи по ID"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, 
                          actual_duration: Optional[int] = None) -> bool:
        """Обновление статуса задачи"""
        try:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            task.status = status
            
            if status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now()
                if actual_duration:
                    task.actual_duration = actual_duration
            
            self._save_tasks()
            return True
            
        except Exception as e:
            print(f"Ошибка обновления статуса задачи: {e}")
            return False
    
    def get_daily_focus(self, focus_date: date) -> Optional[DailyFocus]:
        """Получение ежедневного фокуса по дате"""
        try:
            for focus in self.daily_focus.values():
                if focus.date == focus_date:
                    return focus
            return None
        except Exception as e:
            print(f"Ошибка получения ежедневного фокуса: {e}")
            return None
    
    def get_today_focus(self) -> Optional[DailyFocus]:
        """Получение сегодняшнего фокуса"""
        return self.get_daily_focus(date.today())
    
    def get_focus_tasks(self, focus_id: str) -> List[FocusTask]:
        """Получение задач фокуса"""
        try:
            focus = self.daily_focus.get(focus_id)
            if not focus:
                return []
            
            tasks = []
            for task_id in focus.focus_tasks:
                if task_id in self.tasks:
                    tasks.append(self.tasks[task_id])
            
            return sorted(tasks, key=lambda x: x.priority.value)
        except Exception as e:
            print(f"Ошибка получения задач фокуса: {e}")
            return []
    
    def get_high_priority_tasks(self, limit: int = 3) -> List[FocusTask]:
        """Получение задач высокого приоритета"""
        try:
            high_priority_tasks = [t for t in self.tasks.values() 
                                 if t.priority == PriorityLevel.HIGH and t.status == TaskStatus.PENDING]
            return sorted(high_priority_tasks, key=lambda x: x.created_at)[:limit]
        except Exception as e:
            print(f"Ошибка получения задач высокого приоритета: {e}")
            return []
    
    def get_overdue_tasks(self) -> List[FocusTask]:
        """Получение просроченных задач"""
        try:
            now = datetime.now()
            overdue = []
            for task in self.tasks.values():
                if (task.status == TaskStatus.PENDING and 
                    task.due_date and task.due_date < now):
                    overdue.append(task)
            return sorted(overdue, key=lambda x: x.due_date)
        except Exception as e:
            print(f"Ошибка получения просроченных задач: {e}")
            return []
    
    def add_distraction(self, focus_id: str, distraction: str) -> bool:
        """Добавление отвлечения"""
        try:
            if focus_id in self.daily_focus:
                self.daily_focus[focus_id].distractions.append(distraction)
                self._save_daily_focus()
                return True
        except Exception as e:
            print(f"Ошибка добавления отвлечения: {e}")
        return False
    
    def add_achievement(self, focus_id: str, achievement: str) -> bool:
        """Добавление достижения"""
        try:
            if focus_id in self.daily_focus:
                self.daily_focus[focus_id].achievements.append(achievement)
                self._save_daily_focus()
                return True
        except Exception as e:
            print(f"Ошибка добавления достижения: {e}")
        return False
    
    def update_reflection(self, focus_id: str, reflection: str) -> bool:
        """Обновление рефлексии"""
        try:
            if focus_id in self.daily_focus:
                self.daily_focus[focus_id].reflection = reflection
                self._save_daily_focus()
                return True
        except Exception as e:
            print(f"Ошибка обновления рефлексии: {e}")
        return False
    
    def get_focus_stats(self, focus_id: str) -> Dict[str, Any]:
        """Получение статистики фокуса"""
        try:
            focus = self.daily_focus.get(focus_id)
            if not focus:
                return {}
            
            tasks = self.get_focus_tasks(focus_id)
            completed_tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
            
            return {
                'focus_id': focus_id,
                'date': focus.date.isoformat(),
                'total_tasks': len(tasks),
                'completed_tasks': len(completed_tasks),
                'completion_rate': len(completed_tasks) / max(1, len(tasks)),
                'morning_energy': focus.morning_energy,
                'evening_energy': focus.evening_energy,
                'distractions_count': len(focus.distractions),
                'achievements_count': len(focus.achievements),
                'has_reflection': bool(focus.reflection)
            }
        except Exception as e:
            print(f"Ошибка получения статистики фокуса: {e}")
            return {}
    
    def get_weekly_stats(self, start_date: date) -> Dict[str, Any]:
        """Получение недельной статистики"""
        try:
            end_date = start_date + timedelta(days=7)
            weekly_focus = [f for f in self.daily_focus.values() 
                          if start_date <= f.date < end_date]
            
            total_tasks = 0
            completed_tasks = 0
            total_energy = 0
            total_distractions = 0
            total_achievements = 0
            
            for focus in weekly_focus:
                tasks = self.get_focus_tasks(focus.id)
                total_tasks += len(tasks)
                completed_tasks += len([t for t in tasks if t.status == TaskStatus.COMPLETED])
                total_energy += focus.morning_energy + focus.evening_energy
                total_distractions += len(focus.distractions)
                total_achievements += len(focus.achievements)
            
            return {
                'week_start': start_date.isoformat(),
                'week_end': end_date.isoformat(),
                'focus_days': len(weekly_focus),
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_rate': completed_tasks / max(1, total_tasks),
                'avg_energy': total_energy / max(1, len(weekly_focus) * 2),
                'total_distractions': total_distractions,
                'total_achievements': total_achievements
            }
        except Exception as e:
            print(f"Ошибка получения недельной статистики: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        try:
            total_tasks = len(self.tasks)
            completed_tasks = len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED])
            high_priority_tasks = len([t for t in self.tasks.values() if t.priority == PriorityLevel.HIGH])
            overdue_tasks = len(self.get_overdue_tasks())
            
            return {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_rate': completed_tasks / max(1, total_tasks),
                'high_priority_tasks': high_priority_tasks,
                'overdue_tasks': overdue_tasks,
                'total_focus_days': len(self.daily_focus)
            }
        except Exception as e:
            print(f"Ошибка получения общей статистики: {e}")
            return {}
    
    def export_tasks(self, format: str = "json") -> str:
        """Экспорт задач"""
        try:
            if format == "json":
                return json.dumps({t.id: asdict(t) for t in self.tasks.values()}, 
                                 ensure_ascii=False, indent=2, default=str)
            elif format == "csv":
                import csv
                import io
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(["Title", "Priority", "Status", "Due Date", "Created"])
                for task in self.tasks.values():
                    writer.writerow([
                        task.title,
                        task.priority.value,
                        task.status.value,
                        task.due_date.strftime("%Y-%m-%d") if task.due_date else "",
                        task.created_at.strftime("%Y-%m-%d")
                    ])
                return output.getvalue()
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта задач: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = DailyFocusService()
    
    # Добавляем тестовые задачи
    task1_id = service.add_task(
        title="Важная задача",
        description="Описание важной задачи",
        priority=PriorityLevel.HIGH,
        due_date=datetime.now() + timedelta(days=1)
    )
    
    task2_id = service.add_task(
        title="Средняя задача",
        description="Описание средней задачи",
        priority=PriorityLevel.MEDIUM
    )
    
    # Создаем ежедневный фокус
    focus_id = service.create_daily_focus(
        focus_date=date.today(),
        task_ids=[task1_id, task2_id],
        morning_energy=8,
        evening_energy=6
    )
    
    print(f"Добавлены задачи: {task1_id}, {task2_id}")
    print(f"Создан фокус: {focus_id}")
    print(f"Статистика: {service.get_all_stats()}")
