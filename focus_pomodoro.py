# -*- coding: utf-8 -*-
"""
Фокус-режим и Pomodoro - управление вниманием и продуктивностью
"""

import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging
import psutil
import win32gui
import win32con

try:
    from memory_palace import MemoryPalace
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


class FocusMode(Enum):
    """Режимы фокуса"""
    POMODORO = "pomodoro"
    DEEP_WORK = "deep_work"
    BREAK = "break"
    LONG_BREAK = "long_break"


class AppCategory(Enum):
    """Категории приложений"""
    PRODUCTIVE = "productive"
    DISTRACTING = "distracting"
    NEUTRAL = "neutral"
    BLOCKED = "blocked"


@dataclass
class PomodoroSession:
    """Сессия Pomodoro"""
    id: str
    start_time: str
    duration: int  # минуты
    mode: FocusMode
    completed: bool = False
    breaks_taken: int = 0
    tasks_completed: List[str] = None


@dataclass
class AppUsage:
    """Использование приложения"""
    name: str
    category: AppCategory
    time_spent: int  # секунды
    window_title: str
    is_active: bool = False


@dataclass
class FocusStats:
    """Статистика фокуса"""
    total_sessions: int
    total_focus_time: int  # минуты
    total_breaks: int
    productivity_score: float
    most_used_apps: List[Dict[str, Any]]
    focus_streaks: List[int]


class FocusPomodoro:
    """
    Фокус-режим и Pomodoro таймер
    """
    
    def __init__(self):
        self.logger = logging.getLogger("FocusPomodoro")
        
        # Компоненты
        self.memory_palace = None
        
        # Состояние
        self.current_session = None
        self.is_running = False
        self.focus_mode = FocusMode.POMODORO
        self.blocked_apps = set()
        self.allowed_apps = set()
        
        # Настройки Pomodoro
        self.config = {
            'pomodoro_duration': 25,  # минуты
            'short_break': 5,         # минуты
            'long_break': 15,        # минуты
            'sessions_before_long_break': 4,
            'auto_start_breaks': True,
            'block_distracting_apps': True,
            'show_notifications': True
        }
        
        # Статистика
        self.sessions: List[PomodoroSession] = []
        self.app_usage: Dict[str, AppUsage] = {}
        self.focus_streak = 0
        
        # Категории приложений
        self.app_categories = self._load_app_categories()
        
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
            
            self.logger.info("Компоненты Focus Pomodoro инициализированы")
            
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    def _load_app_categories(self) -> Dict[str, AppCategory]:
        """Загрузка категорий приложений"""
        return {
            # Продуктивные
            'code': AppCategory.PRODUCTIVE,
            'notepad': AppCategory.PRODUCTIVE,
            'word': AppCategory.PRODUCTIVE,
            'excel': AppCategory.PRODUCTIVE,
            'powerpoint': AppCategory.PRODUCTIVE,
            'visual studio': AppCategory.PRODUCTIVE,
            'pycharm': AppCategory.PRODUCTIVE,
            'sublime': AppCategory.PRODUCTIVE,
            'atom': AppCategory.PRODUCTIVE,
            'terminal': AppCategory.PRODUCTIVE,
            'cmd': AppCategory.PRODUCTIVE,
            'powershell': AppCategory.PRODUCTIVE,
            
            # Отвлекающие
            'chrome': AppCategory.DISTRACTING,
            'firefox': AppCategory.DISTRACTING,
            'edge': AppCategory.DISTRACTING,
            'safari': AppCategory.DISTRACTING,
            'youtube': AppCategory.DISTRACTING,
            'facebook': AppCategory.DISTRACTING,
            'instagram': AppCategory.DISTRACTING,
            'twitter': AppCategory.DISTRACTING,
            'telegram': AppCategory.DISTRACTING,
            'whatsapp': AppCategory.DISTRACTING,
            'discord': AppCategory.DISTRACTING,
            'steam': AppCategory.DISTRACTING,
            'spotify': AppCategory.DISTRACTING,
            'netflix': AppCategory.DISTRACTING,
            
            # Нейтральные
            'explorer': AppCategory.NEUTRAL,
            'file manager': AppCategory.NEUTRAL,
            'settings': AppCategory.NEUTRAL,
            'calculator': AppCategory.NEUTRAL,
            'paint': AppCategory.NEUTRAL
        }
    
    async def start_pomodoro(self, task: str = None) -> str:
        """Начало Pomodoro сессии"""
        try:
            if self.is_running:
                self.logger.warning("Сессия уже запущена")
                return None
            
            session_id = f"pomodoro_{len(self.sessions) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            session = PomodoroSession(
                id=session_id,
                start_time=datetime.now().isoformat(),
                duration=self.config['pomodoro_duration'],
                mode=FocusMode.POMODORO,
                tasks_completed=[]
            )
            
            self.current_session = session
            self.is_running = True
            self.focus_mode = FocusMode.POMODORO
            
            # Блокируем отвлекающие приложения
            if self.config['block_distracting_apps']:
                await self._block_distracting_apps()
            
            # Запускаем мониторинг
            self._start_monitoring()
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"Начата Pomodoro сессия: {task or 'Без задачи'}",
                    metadata={
                        'type': 'pomodoro_start',
                        'session_id': session_id,
                        'task': task
                    }
                )
            
            self.logger.info(f"Начата Pomodoro сессия: {session_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Ошибка запуска Pomodoro: {e}")
            return None
    
    async def start_break(self, is_long: bool = False) -> str:
        """Начало перерыва"""
        try:
            if not self.current_session:
                self.logger.warning("Нет активной сессии")
                return None
            
            break_duration = self.config['long_break'] if is_long else self.config['short_break']
            break_mode = FocusMode.LONG_BREAK if is_long else FocusMode.BREAK
            
            # Завершаем текущую сессию
            await self.complete_session()
            
            # Разблокируем приложения
            await self._unblock_apps()
            
            # Начинаем перерыв
            self.focus_mode = break_mode
            self.current_session.mode = break_mode
            self.current_session.duration = break_duration
            
            self.logger.info(f"Начат перерыв: {break_duration} минут")
            return self.current_session.id
            
        except Exception as e:
            self.logger.error(f"Ошибка начала перерыва: {e}")
            return None
    
    async def complete_session(self) -> bool:
        """Завершение сессии"""
        try:
            if not self.current_session:
                return False
            
            # Отмечаем как завершенную
            self.current_session.completed = True
            self.sessions.append(self.current_session)
            
            # Обновляем статистику
            self.focus_streak += 1
            
            # Сохраняем в память
            if self.memory_palace:
                await self.memory_palace.add_memory(
                    content=f"Завершена Pomodoro сессия: {self.current_session.duration} минут",
                    metadata={
                        'type': 'pomodoro_complete',
                        'session_id': self.current_session.id,
                        'duration': self.current_session.duration,
                        'focus_streak': self.focus_streak
                    }
                )
            
            self.logger.info(f"Завершена сессия: {self.current_session.id}")
            
            # Сбрасываем состояние
            self.current_session = None
            self.is_running = False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка завершения сессии: {e}")
            return False
    
    async def _block_distracting_apps(self):
        """Блокировка отвлекающих приложений"""
        try:
            # Получаем список окон
            windows = self._get_active_windows()
            
            for window in windows:
                app_name = window.get('app_name', '').lower()
                window_title = window.get('title', '').lower()
                
                # Проверяем категорию приложения
                category = self._get_app_category(app_name, window_title)
                
                if category == AppCategory.DISTRACTING:
                    # Минимизируем окно
                    hwnd = window.get('hwnd')
                    if hwnd:
                        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
                        self.blocked_apps.add(app_name)
            
            self.logger.info(f"Заблокировано {len(self.blocked_apps)} отвлекающих приложений")
            
        except Exception as e:
            self.logger.error(f"Ошибка блокировки приложений: {e}")
    
    async def _unblock_apps(self):
        """Разблокировка приложений"""
        self.blocked_apps.clear()
        self.logger.info("Приложения разблокированы")
    
    def _get_active_windows(self) -> List[Dict]:
        """Получение активных окон"""
        windows = []
        
        def enum_windows_callback(hwnd, windows):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    # Получаем имя процесса
                    try:
                        _, pid = win32gui.GetWindowThreadProcessId(hwnd)
                        process = psutil.Process(pid)
                        app_name = process.name()
                        
                        windows.append({
                            'hwnd': hwnd,
                            'title': title,
                            'app_name': app_name
                        })
                    except:
                        pass
        
        win32gui.EnumWindows(enum_windows_callback, windows)
        return windows
    
    def _get_app_category(self, app_name: str, window_title: str) -> AppCategory:
        """Определение категории приложения"""
        # Проверяем по имени приложения
        for pattern, category in self.app_categories.items():
            if pattern in app_name.lower():
                return category
        
        # Проверяем по заголовку окна
        for pattern, category in self.app_categories.items():
            if pattern in window_title.lower():
                return category
        
        return AppCategory.NEUTRAL
    
    def _start_monitoring(self):
        """Запуск мониторинга"""
        # Запускаем мониторинг в отдельном потоке
        monitoring_thread = threading.Thread(target=self._monitoring_loop)
        monitoring_thread.daemon = True
        monitoring_thread.start()
    
    def _monitoring_loop(self):
        """Цикл мониторинга"""
        while self.is_running:
            try:
                # Отслеживаем активные приложения
                self._track_app_usage()
                
                # Проверяем время сессии
                if self.current_session:
                    elapsed = datetime.now() - datetime.fromisoformat(self.current_session.start_time)
                    if elapsed.total_seconds() >= self.current_session.duration * 60:
                        # Время истекло
                        asyncio.create_task(self._session_timeout())
                
                time.sleep(5)  # Проверяем каждые 5 секунд
                
            except Exception as e:
                self.logger.error(f"Ошибка мониторинга: {e}")
                time.sleep(10)
    
    def _track_app_usage(self):
        """Отслеживание использования приложений"""
        try:
            windows = self._get_active_windows()
            
            for window in windows:
                app_name = window.get('app_name', '')
                window_title = window.get('title', '')
                
                if app_name not in self.app_usage:
                    self.app_usage[app_name] = AppUsage(
                        name=app_name,
                        category=self._get_app_category(app_name, window_title),
                        time_spent=0,
                        window_title=window_title
                    )
                
                # Увеличиваем время использования
                self.app_usage[app_name].time_spent += 5  # 5 секунд
                self.app_usage[app_name].is_active = True
                
        except Exception as e:
            self.logger.error(f"Ошибка отслеживания приложений: {e}")
    
    async def _session_timeout(self):
        """Обработка истечения времени сессии"""
        if self.current_session:
            if self.current_session.mode == FocusMode.POMODORO:
                # Завершаем Pomodoro, предлагаем перерыв
                await self.complete_session()
                
                # Автоматически начинаем перерыв
                if self.config['auto_start_breaks']:
                    sessions_count = len([s for s in self.sessions if s.mode == FocusMode.POMODORO])
                    is_long_break = sessions_count % self.config['sessions_before_long_break'] == 0
                    await self.start_break(is_long_break)
            
            elif self.current_session.mode in [FocusMode.BREAK, FocusMode.LONG_BREAK]:
                # Завершаем перерыв
                await self.complete_session()
    
    async def get_focus_stats(self) -> FocusStats:
        """Получение статистики фокуса"""
        try:
            total_sessions = len(self.sessions)
            total_focus_time = sum(s.duration for s in self.sessions if s.mode == FocusMode.POMODORO)
            total_breaks = len([s for s in self.sessions if s.mode in [FocusMode.BREAK, FocusMode.LONG_BREAK]])
            
            # Подсчитываем продуктивность
            completed_sessions = len([s for s in self.sessions if s.completed])
            productivity_score = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
            
            # Топ приложений
            most_used_apps = sorted(
                self.app_usage.values(),
                key=lambda x: x.time_spent,
                reverse=True
            )[:5]
            
            # Серии фокуса
            focus_streaks = self._calculate_focus_streaks()
            
            return FocusStats(
                total_sessions=total_sessions,
                total_focus_time=total_focus_time,
                total_breaks=total_breaks,
                productivity_score=productivity_score,
                most_used_apps=[{
                    'name': app.name,
                    'time_spent': app.time_spent,
                    'category': app.category.value
                } for app in most_used_apps],
                focus_streaks=focus_streaks
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            return FocusStats(0, 0, 0, 0, [], [])
    
    def _calculate_focus_streaks(self) -> List[int]:
        """Расчет серий фокуса"""
        streaks = []
        current_streak = 0
        
        for session in self.sessions:
            if session.mode == FocusMode.POMODORO and session.completed:
                current_streak += 1
            else:
                if current_streak > 0:
                    streaks.append(current_streak)
                current_streak = 0
        
        if current_streak > 0:
            streaks.append(current_streak)
        
        return streaks
    
    def format_focus_stats(self, stats: FocusStats) -> str:
        """Форматирование статистики фокуса"""
        text = f"📊 <b>Статистика фокуса</b>\n\n"
        
        text += f"🎯 Всего сессий: {stats.total_sessions}\n"
        text += f"⏱️ Время фокуса: {stats.total_focus_time} мин\n"
        text += f"☕ Перерывов: {stats.total_breaks}\n"
        text += f"📈 Продуктивность: {stats.productivity_score:.1f}%\n\n"
        
        if stats.most_used_apps:
            text += f"💻 <b>Топ приложений:</b>\n"
            for app in stats.most_used_apps:
                minutes = app['time_spent'] // 60
                text += f"• {app['name']}: {minutes} мин ({app['category']})\n"
            text += "\n"
        
        if stats.focus_streaks:
            text += f"🔥 <b>Серии фокуса:</b> {', '.join(map(str, stats.focus_streaks))}\n"
        
        return text
    
    def get_current_status(self) -> Dict[str, Any]:
        """Получение текущего статуса"""
        if not self.current_session:
            return {"status": "idle", "message": "Нет активной сессии"}
        
        elapsed = datetime.now() - datetime.fromisoformat(self.current_session.start_time)
        remaining = self.current_session.duration * 60 - elapsed.total_seconds()
        
        return {
            "status": "active",
            "mode": self.current_session.mode.value,
            "remaining_minutes": int(remaining // 60),
            "remaining_seconds": int(remaining % 60),
            "session_id": self.current_session.id
        }


# Функция для тестирования
async def test_focus_pomodoro():
    """Тестирование фокус-режима"""
    focus = FocusPomodoro()
    
    # Начинаем Pomodoro
    session_id = await focus.start_pomodoro("Тестовая задача")
    print(f"Начата сессия: {session_id}")
    
    # Ждем немного
    await asyncio.sleep(2)
    
    # Получаем статус
    status = focus.get_current_status()
    print(f"Статус: {status}")
    
    # Завершаем сессию
    await focus.complete_session()
    print("Сессия завершена")
    
    # Получаем статистику
    stats = await focus.get_focus_stats()
    print("\nСтатистика:")
    print(focus.format_focus_stats(stats))


if __name__ == "__main__":
    asyncio.run(test_focus_pomodoro())
