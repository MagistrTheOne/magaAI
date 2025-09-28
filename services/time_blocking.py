# -*- coding: utf-8 -*-
"""
Time Blocking Service - тайм-блокинг задач
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, time
from pathlib import Path
import uuid

try:
    from brain.ai_client import BrainManager
    BRAIN_AVAILABLE = True
except ImportError as e:
    print(f"Warning: AI компоненты недоступны: {e}")
    BRAIN_AVAILABLE = False


class TimeBlockingService:
    """
    Сервис тайм-блокинга задач
    """
    
    def __init__(self, storage_dir: str = "storage"):
        self.logger = logging.getLogger("TimeBlocking")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Файлы данных
        self.tasks_file = self.storage_dir / "tasks.json"
        self.blocks_file = self.storage_dir / "time_blocks.json"
        self.schedule_file = self.storage_dir / "schedule.json"
        
        # AI компоненты
        self.brain = None
        
        # Загружаем данные
        self.tasks = self._load_tasks()
        self.time_blocks = self._load_blocks()
        self.schedule = self._load_schedule()
        
        # Инициализация AI
        self._init_ai()
    
    def _init_ai(self):
        """Инициализация AI компонентов"""
        try:
            if BRAIN_AVAILABLE:
                self.brain = BrainManager()
                self.logger.info("AI компоненты инициализированы")
        except Exception as e:
            self.logger.error(f"Ошибка инициализации AI: {e}")
    
    def _load_tasks(self) -> List[Dict[str, Any]]:
        """Загрузка задач"""
        try:
            if self.tasks_file.exists():
                with open(self.tasks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Ошибка загрузки задач: {e}")
            return []
    
    def _save_tasks(self):
        """Сохранение задач"""
        try:
            with open(self.tasks_file, 'w', encoding='utf-8') as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения задач: {e}")
    
    def _load_blocks(self) -> List[Dict[str, Any]]:
        """Загрузка временных блоков"""
        try:
            if self.blocks_file.exists():
                with open(self.blocks_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return []
        except Exception as e:
            self.logger.error(f"Ошибка загрузки блоков: {e}")
            return []
    
    def _save_blocks(self):
        """Сохранение временных блоков"""
        try:
            with open(self.blocks_file, 'w', encoding='utf-8') as f:
                json.dump(self.time_blocks, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения блоков: {e}")
    
    def _load_schedule(self) -> Dict[str, Any]:
        """Загрузка расписания"""
        try:
            if self.schedule_file.exists():
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {
                "work_hours": {"start": "09:00", "end": "18:00"},
                "break_duration": 15,
                "lunch_duration": 60,
                "lunch_time": "13:00",
                "buffer_time": 15
            }
        except Exception as e:
            self.logger.error(f"Ошибка загрузки расписания: {e}")
            return {
                "work_hours": {"start": "09:00", "end": "18:00"},
                "break_duration": 15,
                "lunch_duration": 60,
                "lunch_time": "13:00",
                "buffer_time": 15
            }
    
    def _save_schedule(self):
        """Сохранение расписания"""
        try:
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(self.schedule, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Ошибка сохранения расписания: {e}")
    
    def add_task(self, title: str, description: str = "", priority: str = "medium", 
                 estimated_duration: int = 60, deadline: str = None, 
                 category: str = "work") -> str:
        """Добавление задачи"""
        try:
            task_id = str(uuid.uuid4())
            task = {
                "id": task_id,
                "title": title,
                "description": description,
                "priority": priority,
                "estimated_duration": estimated_duration,  # в минутах
                "deadline": deadline,
                "category": category,
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "scheduled": False
            }
            
            self.tasks.append(task)
            self._save_tasks()
            
            return task_id
        except Exception as e:
            self.logger.error(f"Ошибка добавления задачи: {e}")
            return ""
    
    def get_tasks(self, status: str = None, priority: str = None, 
                  category: str = None) -> List[Dict[str, Any]]:
        """Получение задач с фильтрацией"""
        try:
            filtered_tasks = self.tasks.copy()
            
            if status:
                filtered_tasks = [t for t in filtered_tasks if t.get("status") == status]
            
            if priority:
                filtered_tasks = [t for t in filtered_tasks if t.get("priority") == priority]
            
            if category:
                filtered_tasks = [t for t in filtered_tasks if t.get("category") == category]
            
            # Сортируем по приоритету и дедлайну
            priority_order = {"high": 1, "medium": 2, "low": 3}
            filtered_tasks.sort(key=lambda x: (
                priority_order.get(x.get("priority", "medium"), 2),
                x.get("deadline", "9999-12-31")
            ))
            
            return filtered_tasks
        except Exception as e:
            self.logger.error(f"Ошибка получения задач: {e}")
            return []
    
    async def _ai_schedule_tasks(self, date: str = None) -> List[Dict[str, Any]]:
        """AI планирование задач"""
        try:
            if not self.brain:
                return []
            
            # Получаем незапланированные задачи
            unscheduled = [t for t in self.tasks if not t.get("scheduled", False)]
            
            if not unscheduled:
                return []
            
            # Формируем промпт
            tasks_text = "\n".join([
                f"- {t['title']} ({t['estimated_duration']} мин, {t['priority']} приоритет)"
                for t in unscheduled
            ])
            
            prompt = f"""
Спланируй задачи на день с учетом приоритетов и времени:

Задачи:
{tasks_text}

Рабочие часы: {self.schedule['work_hours']['start']} - {self.schedule['work_hours']['end']}
Обед: {self.schedule['lunch_time']} ({self.schedule['lunch_duration']} мин)
Перерывы: {self.schedule['break_duration']} мин между задачами

Верни JSON с временными блоками:
[
  {{
    "task_id": "id задачи",
    "start_time": "HH:MM",
    "end_time": "HH:MM",
    "reasoning": "обоснование"
  }}
]
            """
            
            response = await self.brain.generate_response(prompt)
            
            # Парсим JSON ответ
            try:
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    schedule_data = json.loads(json_match.group())
                    return schedule_data
            except:
                pass
            
            return []
            
        except Exception as e:
            self.logger.error(f"Ошибка AI планирования: {e}")
            return []
    
    def _calculate_available_slots(self, date: str = None) -> List[Tuple[str, str]]:
        """Расчет доступных временных слотов"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Рабочие часы
            work_start = datetime.strptime(f"{date} {self.schedule['work_hours']['start']}", "%Y-%m-%d %H:%M")
            work_end = datetime.strptime(f"{date} {self.schedule['work_hours']['end']}", "%Y-%m-%d %H:%M")
            
            # Обеденный перерыв
            lunch_start = datetime.strptime(f"{date} {self.schedule['lunch_time']}", "%Y-%m-%d %H:%M")
            lunch_end = lunch_start + timedelta(minutes=self.schedule['lunch_duration'])
            
            # Получаем занятые блоки на этот день
            occupied_blocks = [
                (datetime.fromisoformat(block['start_time']), datetime.fromisoformat(block['end_time']))
                for block in self.time_blocks
                if block.get('date') == date
            ]
            
            # Сортируем занятые блоки
            occupied_blocks.sort()
            
            # Находим свободные слоты
            available_slots = []
            current_time = work_start
            
            # Утренний слот (до обеда)
            if current_time < lunch_start:
                morning_end = min(lunch_start, work_end)
                available_slots.append((current_time, morning_end))
                current_time = lunch_end
            
            # Вечерний слот (после обеда)
            if current_time < work_end:
                available_slots.append((current_time, work_end))
            
            return available_slots
            
        except Exception as e:
            self.logger.error(f"Ошибка расчета слотов: {e}")
            return []
    
    async def schedule_tasks(self, date: str = None, use_ai: bool = True) -> Dict[str, Any]:
        """Планирование задач на день"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            # Получаем незапланированные задачи
            unscheduled_tasks = [t for t in self.tasks if not t.get("scheduled", False)]
            
            if not unscheduled_tasks:
                return {"message": "Нет незапланированных задач", "scheduled": []}
            
            scheduled_blocks = []
            
            if use_ai and self.brain:
                # AI планирование
                ai_schedule = await self._ai_schedule_tasks(date)
                for block in ai_schedule:
                    task_id = block.get("task_id")
                    start_time = block.get("start_time")
                    end_time = block.get("end_time")
                    reasoning = block.get("reasoning", "")
                    
                    # Создаем временной блок
                    time_block = {
                        "id": str(uuid.uuid4()),
                        "task_id": task_id,
                        "date": date,
                        "start_time": f"{date} {start_time}",
                        "end_time": f"{date} {end_time}",
                        "reasoning": reasoning,
                        "created_at": datetime.now().isoformat()
                    }
                    
                    self.time_blocks.append(time_block)
                    scheduled_blocks.append(time_block)
                    
                    # Отмечаем задачу как запланированную
                    for task in self.tasks:
                        if task["id"] == task_id:
                            task["scheduled"] = True
                            break
            else:
                # Простое планирование по приоритету
                available_slots = self._calculate_available_slots(date)
                current_slot = 0
                
                for task in unscheduled_tasks[:5]:  # Максимум 5 задач
                    if current_slot >= len(available_slots):
                        break
                    
                    slot_start, slot_end = available_slots[current_slot]
                    duration = timedelta(minutes=task["estimated_duration"])
                    
                    if slot_start + duration <= slot_end:
                        time_block = {
                            "id": str(uuid.uuid4()),
                            "task_id": task["id"],
                            "date": date,
                            "start_time": slot_start.isoformat(),
                            "end_time": (slot_start + duration).isoformat(),
                            "reasoning": "Простое планирование по приоритету",
                            "created_at": datetime.now().isoformat()
                        }
                        
                        self.time_blocks.append(time_block)
                        scheduled_blocks.append(time_block)
                        
                        # Отмечаем задачу как запланированную
                        task["scheduled"] = True
                        
                        # Переходим к следующему слоту
                        current_slot += 1
            
            # Сохраняем изменения
            self._save_tasks()
            self._save_blocks()
            
            return {
                "date": date,
                "scheduled_count": len(scheduled_blocks),
                "scheduled_blocks": scheduled_blocks
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка планирования: {e}")
            return {"error": str(e)}
    
    def get_schedule(self, date: str = None) -> List[Dict[str, Any]]:
        """Получение расписания на день"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            day_blocks = [
                block for block in self.time_blocks 
                if block.get("date") == date
            ]
            
            # Сортируем по времени начала
            day_blocks.sort(key=lambda x: x.get("start_time", ""))
            
            return day_blocks
        except Exception as e:
            self.logger.error(f"Ошибка получения расписания: {e}")
            return []
    
    def export_schedule_ics(self, date: str = None) -> str:
        """Экспорт расписания в формат iCal"""
        try:
            if not date:
                date = datetime.now().strftime("%Y-%m-%d")
            
            schedule = self.get_schedule(date)
            
            ics_content = [
                "BEGIN:VCALENDAR",
                "VERSION:2.0",
                "PRODID:-//AIMagistr//Time Blocking//EN",
                "CALSCALE:GREGORIAN"
            ]
            
            for block in schedule:
                task = next((t for t in self.tasks if t["id"] == block["task_id"]), {})
                
                start_time = datetime.fromisoformat(block["start_time"])
                end_time = datetime.fromisoformat(block["end_time"])
                
                ics_content.extend([
                    "BEGIN:VEVENT",
                    f"UID:{block['id']}@aimagistr.com",
                    f"DTSTART:{start_time.strftime('%Y%m%dT%H%M%S')}",
                    f"DTEND:{end_time.strftime('%Y%m%dT%H%M%S')}",
                    f"SUMMARY:{task.get('title', 'Задача')}",
                    f"DESCRIPTION:{task.get('description', '')}",
                    f"LOCATION:",
                    "END:VEVENT"
                ])
            
            ics_content.append("END:VCALENDAR")
            
            return "\n".join(ics_content)
            
        except Exception as e:
            self.logger.error(f"Ошибка экспорта iCal: {e}")
            return f"Ошибка: {str(e)}"
    
    def update_schedule_settings(self, settings: Dict[str, Any]) -> bool:
        """Обновление настроек расписания"""
        try:
            self.schedule.update(settings)
            self._save_schedule()
            return True
        except Exception as e:
            self.logger.error(f"Ошибка обновления настроек: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            "total_tasks": len(self.tasks),
            "scheduled_tasks": len([t for t in self.tasks if t.get("scheduled", False)]),
            "pending_tasks": len([t for t in self.tasks if t.get("status") == "pending"]),
            "total_blocks": len(self.time_blocks),
            "ai_available": self.brain is not None,
            "schedule_settings": self.schedule
        }


# Функция для тестирования
async def test_time_blocking():
    """Тестирование сервиса тайм-блокинга"""
    service = TimeBlockingService()
    
    print("Testing Time Blocking Service...")
    
    # Добавляем тестовые задачи
    task1 = service.add_task("Важная встреча", "Обсуждение проекта", "high", 120)
    task2 = service.add_task("Проверить почту", "Обработать входящие", "medium", 30)
    task3 = service.add_task("Планирование", "Составить план на неделю", "low", 60)
    
    print(f"Added tasks: {task1}, {task2}, {task3}")
    
    # Планируем задачи
    result = await service.schedule_tasks()
    print(f"Schedule result: {result}")
    
    # Получаем расписание
    schedule = service.get_schedule()
    print(f"Schedule: {schedule}")
    
    # Экспортируем в iCal
    ics = service.export_schedule_ics()
    print(f"iCal export: {ics[:200]}...")
    
    # Статистика
    stats = service.get_stats()
    print(f"Stats: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_time_blocking())
