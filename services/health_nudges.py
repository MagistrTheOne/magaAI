# -*- coding: utf-8 -*-
"""
AIMagistr 3.1 - Помодоро/перерывы/вода/осанка нуджи
"""

import json
import os
from datetime import datetime, timedelta, time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

class NudgeType(Enum):
    POMODORO = "pomodoro"
    BREAK = "break"
    WATER = "water"
    POSTURE = "posture"
    EXERCISE = "exercise"
    EYE_REST = "eye_rest"
    STRETCH = "stretch"

class NudgeStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"

@dataclass
class Nudge:
    id: str
    nudge_type: NudgeType
    title: str
    message: str
    scheduled_time: datetime
    status: NudgeStatus = NudgeStatus.PENDING
    created_at: datetime = None
    sent_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    priority: int = 3  # 1-5, где 5 - высший приоритет
    repeat_interval: Optional[int] = None  # в минутах
    tags: List[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.tags is None:
            self.tags = []

@dataclass
class PomodoroSession:
    id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: int = 25  # в минутах
    break_duration: int = 5  # в минутах
    task_description: str = ""
    completed: bool = False
    interrupted: bool = False
    notes: str = ""

@dataclass
class HealthMetric:
    id: str
    metric_type: str  # water, steps, exercise, etc.
    value: float
    unit: str
    recorded_at: datetime
    notes: str = ""

class HealthNudgesService:
    """Сервис здоровья и продуктивности"""
    
    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        self.nudges_file = self.storage_dir / "health_nudges.json"
        self.pomodoro_file = self.storage_dir / "pomodoro_sessions.json"
        self.metrics_file = self.storage_dir / "health_metrics.json"
        
        # Загружаем данные
        self.nudges = self._load_nudges()
        self.pomodoro_sessions = self._load_pomodoro_sessions()
        self.health_metrics = self._load_health_metrics()
    
    def _load_nudges(self) -> Dict[str, Nudge]:
        """Загрузка нуджей из файла"""
        try:
            if self.nudges_file.exists():
                with open(self.nudges_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    nudges = {}
                    for nudge_id, nudge_data in data.items():
                        nudge_data['nudge_type'] = NudgeType(nudge_data['nudge_type'])
                        nudge_data['status'] = NudgeStatus(nudge_data['status'])
                        nudge_data['scheduled_time'] = datetime.fromisoformat(nudge_data['scheduled_time'])
                        nudge_data['created_at'] = datetime.fromisoformat(nudge_data['created_at'])
                        if nudge_data.get('sent_at'):
                            nudge_data['sent_at'] = datetime.fromisoformat(nudge_data['sent_at'])
                        if nudge_data.get('acknowledged_at'):
                            nudge_data['acknowledged_at'] = datetime.fromisoformat(nudge_data['acknowledged_at'])
                        nudges[nudge_id] = Nudge(**nudge_data)
                    return nudges
        except Exception as e:
            print(f"Ошибка загрузки нуджей: {e}")
        return {}
    
    def _save_nudges(self):
        """Сохранение нуджей в файл"""
        try:
            data = {}
            for nudge_id, nudge in self.nudges.items():
                nudge_dict = asdict(nudge)
                nudge_dict['nudge_type'] = nudge.nudge_type.value
                nudge_dict['status'] = nudge.status.value
                nudge_dict['scheduled_time'] = nudge.scheduled_time.isoformat()
                nudge_dict['created_at'] = nudge.created_at.isoformat()
                if nudge.sent_at:
                    nudge_dict['sent_at'] = nudge.sent_at.isoformat()
                if nudge.acknowledged_at:
                    nudge_dict['acknowledged_at'] = nudge.acknowledged_at.isoformat()
                data[nudge_id] = nudge_dict
            
            with open(self.nudges_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения нуджей: {e}")
    
    def _load_pomodoro_sessions(self) -> Dict[str, PomodoroSession]:
        """Загрузка сессий помодоро из файла"""
        try:
            if self.pomodoro_file.exists():
                with open(self.pomodoro_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions = {}
                    for session_id, session_data in data.items():
                        session_data['start_time'] = datetime.fromisoformat(session_data['start_time'])
                        if session_data.get('end_time'):
                            session_data['end_time'] = datetime.fromisoformat(session_data['end_time'])
                        sessions[session_id] = PomodoroSession(**session_data)
                    return sessions
        except Exception as e:
            print(f"Ошибка загрузки сессий помодоро: {e}")
        return {}
    
    def _save_pomodoro_sessions(self):
        """Сохранение сессий помодоро в файл"""
        try:
            data = {}
            for session_id, session in self.pomodoro_sessions.items():
                session_dict = asdict(session)
                session_dict['start_time'] = session.start_time.isoformat()
                if session.end_time:
                    session_dict['end_time'] = session.end_time.isoformat()
                data[session_id] = session_dict
            
            with open(self.pomodoro_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения сессий помодоро: {e}")
    
    def _load_health_metrics(self) -> Dict[str, HealthMetric]:
        """Загрузка метрик здоровья из файла"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metrics = {}
                    for metric_id, metric_data in data.items():
                        metric_data['recorded_at'] = datetime.fromisoformat(metric_data['recorded_at'])
                        metrics[metric_id] = HealthMetric(**metric_data)
                    return metrics
        except Exception as e:
            print(f"Ошибка загрузки метрик здоровья: {e}")
        return {}
    
    def _save_health_metrics(self):
        """Сохранение метрик здоровья в файл"""
        try:
            data = {}
            for metric_id, metric in self.health_metrics.items():
                metric_dict = asdict(metric)
                metric_dict['recorded_at'] = metric.recorded_at.isoformat()
                data[metric_id] = metric_dict
            
            with open(self.metrics_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения метрик здоровья: {e}")
    
    def create_nudge(self, nudge_type: NudgeType, title: str, message: str,
                    scheduled_time: datetime, priority: int = 3,
                    repeat_interval: int = None, tags: List[str] = None) -> str:
        """Создание нуджа"""
        try:
            nudge_id = str(uuid.uuid4())
            
            nudge = Nudge(
                id=nudge_id,
                nudge_type=nudge_type,
                title=title,
                message=message,
                scheduled_time=scheduled_time,
                priority=priority,
                repeat_interval=repeat_interval,
                tags=tags or []
            )
            
            self.nudges[nudge_id] = nudge
            self._save_nudges()
            
            return nudge_id
            
        except Exception as e:
            print(f"Ошибка создания нуджа: {e}")
            return None
    
    def create_pomodoro_nudges(self, work_duration: int = 25, break_duration: int = 5,
                              start_time: datetime = None, count: int = 4) -> List[str]:
        """Создание серии нуджей для помодоро"""
        try:
            if start_time is None:
                start_time = datetime.now()
            
            nudge_ids = []
            current_time = start_time
            
            for i in range(count):
                # Нудж для начала работы
                work_nudge_id = self.create_nudge(
                    nudge_type=NudgeType.POMODORO,
                    title=f"Помодоро {i+1}/{count}",
                    message=f"Время работать! {work_duration} минут фокуса.",
                    scheduled_time=current_time,
                    priority=5,
                    tags=["pomodoro", "work"]
                )
                nudge_ids.append(work_nudge_id)
                
                # Нудж для перерыва
                break_time = current_time + timedelta(minutes=work_duration)
                break_nudge_id = self.create_nudge(
                    nudge_type=NudgeType.BREAK,
                    title=f"Перерыв {i+1}/{count}",
                    message=f"Время отдохнуть! {break_duration} минут перерыва.",
                    scheduled_time=break_time,
                    priority=4,
                    tags=["pomodoro", "break"]
                )
                nudge_ids.append(break_nudge_id)
                
                current_time = break_time + timedelta(minutes=break_duration)
            
            return nudge_ids
            
        except Exception as e:
            print(f"Ошибка создания нуджей помодоро: {e}")
            return []
    
    def create_water_reminders(self, start_time: datetime = None, 
                              interval_minutes: int = 60) -> List[str]:
        """Создание напоминаний о воде"""
        try:
            if start_time is None:
                start_time = datetime.now()
            
            nudge_ids = []
            current_time = start_time
            
            # Создаем напоминания на 8 часов (рабочий день)
            for i in range(8):
                nudge_id = self.create_nudge(
                    nudge_type=NudgeType.WATER,
                    title="Время пить воду",
                    message="Не забудьте выпить стакан воды! 💧",
                    scheduled_time=current_time,
                    priority=3,
                    tags=["water", "health"]
                )
                nudge_ids.append(nudge_id)
                current_time += timedelta(minutes=interval_minutes)
            
            return nudge_ids
            
        except Exception as e:
            print(f"Ошибка создания напоминаний о воде: {e}")
            return []
    
    def create_posture_reminders(self, start_time: datetime = None,
                                 interval_minutes: int = 30) -> List[str]:
        """Создание напоминаний об осанке"""
        try:
            if start_time is None:
                start_time = datetime.now()
            
            nudge_ids = []
            current_time = start_time
            
            # Создаем напоминания на 8 часов
            for i in range(16):  # каждые 30 минут
                nudge_id = self.create_nudge(
                    nudge_type=NudgeType.POSTURE,
                    title="Проверьте осанку",
                    message="Выпрямите спину, расслабьте плечи! 🧘",
                    scheduled_time=current_time,
                    priority=2,
                    tags=["posture", "health"]
                )
                nudge_ids.append(nudge_id)
                current_time += timedelta(minutes=interval_minutes)
            
            return nudge_ids
            
        except Exception as e:
            print(f"Ошибка создания напоминаний об осанке: {e}")
            return []
    
    def start_pomodoro_session(self, task_description: str = "", 
                              duration: int = 25, break_duration: int = 5) -> str:
        """Начало сессии помодоро"""
        try:
            session_id = str(uuid.uuid4())
            
            session = PomodoroSession(
                id=session_id,
                start_time=datetime.now(),
                duration=duration,
                break_duration=break_duration,
                task_description=task_description
            )
            
            self.pomodoro_sessions[session_id] = session
            self._save_pomodoro_sessions()
            
            return session_id
            
        except Exception as e:
            print(f"Ошибка начала сессии помодоро: {e}")
            return None
    
    def complete_pomodoro_session(self, session_id: str, completed: bool = True,
                                 interrupted: bool = False, notes: str = "") -> bool:
        """Завершение сессии помодоро"""
        try:
            if session_id not in self.pomodoro_sessions:
                return False
            
            session = self.pomodoro_sessions[session_id]
            session.end_time = datetime.now()
            session.completed = completed
            session.interrupted = interrupted
            session.notes = notes
            
            self._save_pomodoro_sessions()
            return True
            
        except Exception as e:
            print(f"Ошибка завершения сессии помодоро: {e}")
            return False
    
    def record_health_metric(self, metric_type: str, value: float, unit: str,
                           notes: str = "") -> str:
        """Запись метрики здоровья"""
        try:
            metric_id = str(uuid.uuid4())
            
            metric = HealthMetric(
                id=metric_id,
                metric_type=metric_type,
                value=value,
                unit=unit,
                recorded_at=datetime.now(),
                notes=notes
            )
            
            self.health_metrics[metric_id] = metric
            self._save_health_metrics()
            
            return metric_id
            
        except Exception as e:
            print(f"Ошибка записи метрики здоровья: {e}")
            return None
    
    def get_pending_nudges(self) -> List[Nudge]:
        """Получение ожидающих нуджей"""
        try:
            now = datetime.now()
            pending = []
            for nudge in self.nudges.values():
                if (nudge.status == NudgeStatus.PENDING and 
                    nudge.scheduled_time <= now):
                    pending.append(nudge)
            return sorted(pending, key=lambda x: x.scheduled_time)
        except Exception as e:
            print(f"Ошибка получения ожидающих нуджей: {e}")
            return []
    
    def acknowledge_nudge(self, nudge_id: str) -> bool:
        """Подтверждение нуджа"""
        try:
            if nudge_id not in self.nudges:
                return False
            
            nudge = self.nudges[nudge_id]
            nudge.status = NudgeStatus.ACKNOWLEDGED
            nudge.acknowledged_at = datetime.now()
            
            # Если есть повтор, создаем следующий нудж
            if nudge.repeat_interval:
                next_time = nudge.scheduled_time + timedelta(minutes=nudge.repeat_interval)
                self.create_nudge(
                    nudge_type=nudge.nudge_type,
                    title=nudge.title,
                    message=nudge.message,
                    scheduled_time=next_time,
                    priority=nudge.priority,
                    repeat_interval=nudge.repeat_interval,
                    tags=nudge.tags
                )
            
            self._save_nudges()
            return True
            
        except Exception as e:
            print(f"Ошибка подтверждения нуджа: {e}")
            return False
    
    def get_pomodoro_stats(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Получение статистики помодоро за период"""
        try:
            sessions_in_period = []
            for session in self.pomodoro_sessions.values():
                if start_date <= session.start_time.date() <= end_date:
                    sessions_in_period.append(session)
            
            total_sessions = len(sessions_in_period)
            completed_sessions = len([s for s in sessions_in_period if s.completed])
            interrupted_sessions = len([s for s in sessions_in_period if s.interrupted])
            
            total_work_time = sum(s.duration for s in sessions_in_period if s.completed)
            avg_session_duration = total_work_time / max(1, completed_sessions)
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'interrupted_sessions': interrupted_sessions,
                'completion_rate': completed_sessions / max(1, total_sessions),
                'total_work_time': total_work_time,
                'avg_session_duration': avg_session_duration
            }
        except Exception as e:
            print(f"Ошибка получения статистики помодоро: {e}")
            return {}
    
    def get_health_metrics_summary(self, metric_type: str, days: int = 7) -> Dict[str, Any]:
        """Получение сводки по метрикам здоровья"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_metrics = [m for m in self.health_metrics.values() 
                            if m.metric_type == metric_type and m.recorded_at >= cutoff_date]
            
            if not recent_metrics:
                return {}
            
            values = [m.value for m in recent_metrics]
            total_value = sum(values)
            avg_value = total_value / len(values)
            max_value = max(values)
            min_value = min(values)
            
            return {
                'metric_type': metric_type,
                'period_days': days,
                'total_records': len(recent_metrics),
                'total_value': total_value,
                'avg_value': avg_value,
                'max_value': max_value,
                'min_value': min_value,
                'latest_value': recent_metrics[-1].value if recent_metrics else None
            }
        except Exception as e:
            print(f"Ошибка получения сводки по метрикам здоровья: {e}")
            return {}
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Получение общей статистики"""
        try:
            total_nudges = len(self.nudges)
            pending_nudges = len([n for n in self.nudges.values() if n.status == NudgeStatus.PENDING])
            acknowledged_nudges = len([n for n in self.nudges.values() if n.status == NudgeStatus.ACKNOWLEDGED])
            
            total_pomodoro_sessions = len(self.pomodoro_sessions)
            completed_sessions = len([s for s in self.pomodoro_sessions.values() if s.completed])
            
            total_health_metrics = len(self.health_metrics)
            
            return {
                'total_nudges': total_nudges,
                'pending_nudges': pending_nudges,
                'acknowledged_nudges': acknowledged_nudges,
                'total_pomodoro_sessions': total_pomodoro_sessions,
                'completed_sessions': completed_sessions,
                'pomodoro_completion_rate': completed_sessions / max(1, total_pomodoro_sessions),
                'total_health_metrics': total_health_metrics
            }
        except Exception as e:
            print(f"Ошибка получения общей статистики: {e}")
            return {}
    
    def export_health_data(self, format: str = "json") -> str:
        """Экспорт данных о здоровье"""
        try:
            if format == "json":
                data = {
                    'nudges': {n.id: asdict(n) for n in self.nudges.values()},
                    'pomodoro_sessions': {s.id: asdict(s) for s in self.pomodoro_sessions.values()},
                    'health_metrics': {m.id: asdict(m) for m in self.health_metrics.values()}
                }
                return json.dumps(data, ensure_ascii=False, indent=2, default=str)
            else:
                return "Unsupported format"
        except Exception as e:
            print(f"Ошибка экспорта данных о здоровье: {e}")
            return ""

# Тестирование
if __name__ == "__main__":
    service = HealthNudgesService()
    
    # Создаем нуджи для помодоро
    pomodoro_nudges = service.create_pomodoro_nudges(count=2)
    print(f"Созданы нуджи помодоро: {len(pomodoro_nudges)}")
    
    # Создаем напоминания о воде
    water_nudges = service.create_water_reminders()
    print(f"Созданы напоминания о воде: {len(water_nudges)}")
    
    # Начинаем сессию помодоро
    session_id = service.start_pomodoro_session("Работа над проектом")
    print(f"Начата сессия помодоро: {session_id}")
    
    # Записываем метрику здоровья
    metric_id = service.record_health_metric("water", 250, "ml", "Утренний стакан воды")
    print(f"Записана метрика здоровья: {metric_id}")
    
    print(f"Статистика: {service.get_all_stats()}")
