# -*- coding: utf-8 -*-
"""
Overlay HUD Module
Экранный HUD с подсказками, статусами и хоткеями
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Optional, Dict, List, Callable
from enum import Enum
import json


class HUDStatus(Enum):
    """Статусы HUD"""
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"
    IDLE = "idle"
    ERROR = "error"


class OverlayHUD:
    """
    Ненавязчивый overlay HUD для отображения статусов
    """
    
    def __init__(self, 
                 on_hotkey: Optional[Callable] = None,
                 position: str = "top-right"):
        """
        Args:
            on_hotkey: Callback при нажатии хоткея
            position: Позиция HUD на экране
        """
        self.on_hotkey = on_hotkey
        self.position = position
        
        # Состояние
        self.is_visible = False
        self.current_status = HUDStatus.IDLE
        self.status_text = ""
        self.progress = 0
        self.hotkeys = {}
        
        # GUI элементы
        self.root = None
        self.status_label = None
        self.progress_bar = None
        self.hotkey_labels = []
        
        # Настройки
        self.auto_hide_delay = 5.0  # секунд
        self.last_activity = time.time()
        self.auto_hide_timer = None
        
        # Инициализация
        self._initialize_hud()
        
    def _initialize_hud(self):
        """Инициализация HUD"""
        try:
            # Создаем окно HUD
            self.root = tk.Tk()
            self.root.title("AI Assistant HUD")
            self.root.attributes('-topmost', True)
            self.root.attributes('-alpha', 0.9)
            self.root.overrideredirect(True)
            
            # Настраиваем размер и позицию
            self._setup_window_geometry()
            
            # Создаем элементы интерфейса
            self._create_widgets()
            
            # Настраиваем хоткеи
            self._setup_hotkeys()
            
            # Запускаем автоскрытие
            self._start_auto_hide_timer()
            
        except Exception as e:
            print(f"[OverlayHUD] Ошибка инициализации: {e}")
            
    def _setup_window_geometry(self):
        """Настройка геометрии окна"""
        # Размер окна
        width = 300
        height = 150
        
        # Получаем размер экрана
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Позиционируем в зависимости от настройки
        if self.position == "top-right":
            x = screen_width - width - 20
            y = 20
        elif self.position == "top-left":
            x = 20
            y = 20
        elif self.position == "bottom-right":
            x = screen_width - width - 20
            y = screen_height - height - 20
        elif self.position == "bottom-left":
            x = 20
            y = screen_height - height - 20
        else:
            x = screen_width - width - 20
            y = 20
            
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
    def _create_widgets(self):
        """Создание элементов интерфейса"""
        # Основной фрейм
        main_frame = tk.Frame(self.root, bg='#2b2b2b', relief='raised', bd=2)
        main_frame.pack(fill='both', expand=True)
        
        # Заголовок
        title_label = tk.Label(main_frame, text="AI Assistant", 
                              font=('Arial', 10, 'bold'), 
                              bg='#2b2b2b', fg='#00ff00')
        title_label.pack(pady=5)
        
        # Статус
        self.status_label = tk.Label(main_frame, text="Idle", 
                                    font=('Arial', 9), 
                                    bg='#2b2b2b', fg='white')
        self.status_label.pack(pady=2)
        
        # Прогресс бар
        self.progress_bar = ttk.Progressbar(main_frame, mode='determinate', 
                                          style='TProgressbar')
        self.progress_bar.pack(fill='x', padx=10, pady=5)
        
        # Хоткеи
        hotkeys_frame = tk.Frame(main_frame, bg='#2b2b2b')
        hotkeys_frame.pack(fill='x', padx=10, pady=5)
        
        # Добавляем хоткеи
        self._add_hotkey_label(hotkeys_frame, "F9", "Listen")
        self._add_hotkey_label(hotkeys_frame, "F10", "Mute")
        self._add_hotkey_label(hotkeys_frame, "F11", "Intro")
        
    def _add_hotkey_label(self, parent, key, action):
        """Добавление лейбла хоткея"""
        hotkey_label = tk.Label(parent, text=f"{key}: {action}", 
                               font=('Arial', 8), 
                               bg='#2b2b2b', fg='#9aa7b0')
        hotkey_label.pack(side='left', padx=5)
        self.hotkey_labels.append(hotkey_label)
        
    def _setup_hotkeys(self):
        """Настройка хоткеев"""
        self.hotkeys = {
            'F9': self._on_listen_hotkey,
            'F10': self._on_mute_hotkey,
            'F11': self._on_intro_hotkey,
            'Escape': self._on_escape_hotkey
        }
        
        # Привязываем хоткеи
        for key, callback in self.hotkeys.items():
            self.root.bind(f'<{key}>', lambda e, cb=callback: cb())
            
    def _on_listen_hotkey(self):
        """Обработка хоткея Listen"""
        if self.on_hotkey:
            self.on_hotkey('listen')
            
    def _on_mute_hotkey(self):
        """Обработка хоткея Mute"""
        if self.on_hotkey:
            self.on_hotkey('mute')
            
    def _on_intro_hotkey(self):
        """Обработка хоткея Intro"""
        if self.on_hotkey:
            self.on_hotkey('intro')
            
    def _on_escape_hotkey(self):
        """Обработка хоткея Escape"""
        self.hide()
        
    def show(self):
        """Показать HUD"""
        if not self.is_visible:
            self.is_visible = True
            self.root.deiconify()
            self._update_activity()
            
    def hide(self):
        """Скрыть HUD"""
        if self.is_visible:
            self.is_visible = False
            self.root.withdraw()
            
    def toggle(self):
        """Переключить видимость HUD"""
        if self.is_visible:
            self.hide()
        else:
            self.show()
            
    def set_status(self, status: HUDStatus, text: str = ""):
        """Установить статус HUD"""
        self.current_status = status
        self.status_text = text
        
        if self.status_label:
            # Обновляем текст статуса
            status_text = f"{status.value.title()}"
            if text:
                status_text += f": {text}"
                
            self.status_label.config(text=status_text)
            
            # Обновляем цвет в зависимости от статуса
            color_map = {
                HUDStatus.LISTENING: '#00ff00',
                HUDStatus.SPEAKING: '#ff6b35',
                HUDStatus.PROCESSING: '#2196f3',
                HUDStatus.IDLE: '#9aa7b0',
                HUDStatus.ERROR: '#ff0000'
            }
            
            self.status_label.config(fg=color_map.get(status, '#9aa7b0'))
            
        self._update_activity()
        
    def set_progress(self, progress: int):
        """Установить прогресс (0-100)"""
        self.progress = max(0, min(100, progress))
        
        if self.progress_bar:
            self.progress_bar['value'] = self.progress
            
        self._update_activity()
        
    def set_text(self, text: str):
        """Установить текст статуса"""
        self.status_text = text
        
        if self.status_label:
            status_text = f"{self.current_status.value.title()}"
            if text:
                status_text += f": {text}"
                
            self.status_label.config(text=status_text)
            
        self._update_activity()
        
    def _update_activity(self):
        """Обновить время последней активности"""
        self.last_activity = time.time()
        
        # Сбрасываем таймер автоскрытия
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            
        self._start_auto_hide_timer()
        
    def _start_auto_hide_timer(self):
        """Запуск таймера автоскрытия"""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            
        self.auto_hide_timer = threading.Timer(self.auto_hide_delay, self._auto_hide)
        self.auto_hide_timer.start()
        
    def _auto_hide(self):
        """Автоматическое скрытие HUD"""
        if time.time() - self.last_activity > self.auto_hide_delay:
            self.hide()
            
    def set_position(self, position: str):
        """Изменить позицию HUD"""
        self.position = position
        self._setup_window_geometry()
        
    def set_auto_hide_delay(self, delay: float):
        """Установить задержку автоскрытия"""
        self.auto_hide_delay = delay
        
    def add_hotkey(self, key: str, action: str, callback: Callable):
        """Добавить хоткей"""
        self.hotkeys[key] = callback
        
        # Привязываем хоткей
        self.root.bind(f'<{key}>', lambda e, cb=callback: cb())
        
        # Добавляем в интерфейс
        self._add_hotkey_label(self.root.winfo_children()[0], key, action)
        
    def remove_hotkey(self, key: str):
        """Удалить хоткей"""
        if key in self.hotkeys:
            del self.hotkeys[key]
            self.root.unbind(f'<{key}>')
            
    def get_status(self) -> Dict:
        """Получить текущий статус HUD"""
        return {
            'is_visible': self.is_visible,
            'current_status': self.current_status.value,
            'status_text': self.status_text,
            'progress': self.progress,
            'position': self.position
        }
        
    def run(self):
        """Запуск HUD"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"[OverlayHUD] Ошибка запуска: {e}")
            
    def destroy(self):
        """Уничтожение HUD"""
        if self.auto_hide_timer:
            self.auto_hide_timer.cancel()
            
        if self.root:
            self.root.destroy()
            
    def is_running(self) -> bool:
        """Проверить, запущен ли HUD"""
        return self.root is not None and self.root.winfo_exists()
