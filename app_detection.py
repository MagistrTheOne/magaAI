# -*- coding: utf-8 -*-
"""
App Detection Module
Детект процессов Zoom/Telegram/Discord и быстрые действия
"""

import time
import threading
import subprocess
import psutil
import pygetwindow as gw
from typing import List, Dict, Optional, Callable
import os


class AppDetector:
    """
    Детектор приложений и процессов
    """
    
    def __init__(self, 
                 on_app_detected: Optional[Callable] = None,
                 scan_interval: float = 5.0):
        """
        Args:
            on_app_detected: Callback при обнаружении приложения
            scan_interval: Интервал сканирования в секундах
        """
        self.on_app_detected = on_app_detected
        self.scan_interval = scan_interval
        
        # Состояние
        self.is_monitoring = False
        self.monitor_thread = None
        self.detected_apps = {}
        self.app_history = []
        
        # Целевые приложения
        self.target_apps = {
            'zoom': {
                'processes': ['Zoom.exe', 'ZoomLauncher.exe'],
                'windows': ['Zoom', 'Zoom Meeting'],
                'launch_cmd': None,  # Будет определен автоматически
                'priority': 1
            },
            'telegram': {
                'processes': ['Telegram.exe'],
                'windows': ['Telegram'],
                'launch_cmd': None,
                'priority': 2
            },
            'discord': {
                'processes': ['Discord.exe'],
                'windows': ['Discord'],
                'launch_cmd': None,
                'priority': 3
            },
            'teams': {
                'processes': ['ms-teams.exe', 'Teams.exe'],
                'windows': ['Microsoft Teams'],
                'launch_cmd': None,
                'priority': 4
            },
            'outlook': {
                'processes': ['OUTLOOK.EXE'],
                'windows': ['Microsoft Outlook'],
                'launch_cmd': None,
                'priority': 5
            }
        }
        
    def start_monitoring(self):
        """Запуск мониторинга приложений"""
        if self.is_monitoring:
            return
            
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        """Остановка мониторинга приложений"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)
            
    def _monitor_worker(self):
        """Поток мониторинга приложений"""
        while self.is_monitoring:
            try:
                # Сканируем процессы
                running_apps = self._scan_processes()
                
                # Сканируем окна
                window_apps = self._scan_windows()
                
                # Объединяем результаты
                all_apps = {**running_apps, **window_apps}
                
                # Проверяем изменения
                self._check_app_changes(all_apps)
                
                self.detected_apps = all_apps
                
            except Exception as e:
                print(f"[AppDetector] Ошибка мониторинга: {e}")
                
            time.sleep(self.scan_interval)
            
    def _scan_processes(self) -> Dict[str, Dict]:
        """Сканирование запущенных процессов"""
        detected = {}
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    proc_name = proc.info['name']
                    proc_exe = proc.info['exe']
                    
                    # Проверяем каждое целевое приложение
                    for app_name, app_info in self.target_apps.items():
                        for target_process in app_info['processes']:
                            if target_process.lower() in proc_name.lower():
                                detected[app_name] = {
                                    'type': 'process',
                                    'name': app_name,
                                    'pid': proc.info['pid'],
                                    'process_name': proc_name,
                                    'exe_path': proc_exe,
                                    'detected_at': time.time(),
                                    'status': 'running'
                                }
                                break
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            print(f"[AppDetector] Ошибка сканирования процессов: {e}")
            
        return detected
        
    def _scan_windows(self) -> Dict[str, Dict]:
        """Сканирование окон приложений"""
        detected = {}
        
        try:
            windows = gw.getAllWindows()
            
            for window in windows:
                if not window.visible or not window.title:
                    continue
                    
                window_title = window.title.lower()
                
                # Проверяем каждое целевое приложение
                for app_name, app_info in self.target_apps.items():
                    for target_window in app_info['windows']:
                        if target_window.lower() in window_title:
                            detected[app_name] = {
                                'type': 'window',
                                'name': app_name,
                                'window_title': window.title,
                                'window_rect': (window.left, window.top, window.width, window.height),
                                'detected_at': time.time(),
                                'status': 'visible'
                            }
                            break
                            
        except Exception as e:
            print(f"[AppDetector] Ошибка сканирования окон: {e}")
            
        return detected
        
    def _check_app_changes(self, current_apps: Dict[str, Dict]):
        """Проверка изменений в приложениях"""
        # Новые приложения
        for app_name, app_info in current_apps.items():
            if app_name not in self.detected_apps:
                self._on_app_detected(app_name, app_info, 'started')
                
        # Закрытые приложения
        for app_name, app_info in self.detected_apps.items():
            if app_name not in current_apps:
                self._on_app_detected(app_name, app_info, 'stopped')
                
    def _on_app_detected(self, app_name: str, app_info: Dict, action: str):
        """Обработка обнаружения приложения"""
        try:
            # Логируем в историю
            log_entry = {
                'app_name': app_name,
                'action': action,
                'app_info': app_info,
                'timestamp': time.time()
            }
            self.app_history.append(log_entry)
            
            # Ограничиваем историю
            if len(self.app_history) > 1000:
                self.app_history = self.app_history[-500:]
                
            # Вызываем callback
            if self.on_app_detected:
                self.on_app_detected(app_name, app_info, action)
                
        except Exception as e:
            print(f"[AppDetector] Ошибка обработки обнаружения: {e}")
            
    def launch_app(self, app_name: str) -> bool:
        """Запуск приложения"""
        try:
            if app_name not in self.target_apps:
                return False
                
            app_info = self.target_apps[app_name]
            
            # Пытаемся найти исполняемый файл
            exe_path = self._find_app_executable(app_name)
            if exe_path and os.path.exists(exe_path):
                subprocess.Popen([exe_path], shell=True)
                return True
            else:
                # Пытаемся запустить через Start Menu
                return self._launch_via_start_menu(app_name)
                
        except Exception as e:
            print(f"[AppDetector] Ошибка запуска {app_name}: {e}")
            return False
            
    def _find_app_executable(self, app_name: str) -> Optional[str]:
        """Поиск исполняемого файла приложения"""
        try:
            # Стандартные пути
            common_paths = {
                'zoom': [
                    r'C:\Program Files\Zoom\bin\Zoom.exe',
                    r'C:\Program Files (x86)\Zoom\bin\Zoom.exe',
                    r'%APPDATA%\Zoom\bin\Zoom.exe'
                ],
                'telegram': [
                    r'C:\Users\%USERNAME%\AppData\Roaming\Telegram Desktop\Telegram.exe',
                    r'%APPDATA%\Telegram Desktop\Telegram.exe'
                ],
                'discord': [
                    r'C:\Users\%USERNAME%\AppData\Local\Discord\app-*\Discord.exe',
                    r'%LOCALAPPDATA%\Discord\app-*\Discord.exe'
                ],
                'teams': [
                    r'C:\Users\%USERNAME%\AppData\Local\Microsoft\Teams\current\Teams.exe',
                    r'%LOCALAPPDATA%\Microsoft\Teams\current\Teams.exe'
                ],
                'outlook': [
                    r'C:\Program Files\Microsoft Office\root\Office16\OUTLOOK.EXE',
                    r'C:\Program Files (x86)\Microsoft Office\root\Office16\OUTLOOK.EXE'
                ]
            }
            
            if app_name in common_paths:
                for path_template in common_paths[app_name]:
                    expanded_path = os.path.expandvars(path_template)
                    if os.path.exists(expanded_path):
                        return expanded_path
                        
            return None
            
        except Exception as e:
            print(f"[AppDetector] Ошибка поиска исполняемого файла: {e}")
            return None
            
    def _launch_via_start_menu(self, app_name: str) -> bool:
        """Запуск через Start Menu"""
        try:
            start_menu_names = {
                'zoom': 'Zoom',
                'telegram': 'Telegram',
                'discord': 'Discord',
                'teams': 'Microsoft Teams',
                'outlook': 'Microsoft Outlook'
            }
            
            if app_name in start_menu_names:
                app_display_name = start_menu_names[app_name]
                # Используем PowerShell для запуска через Start Menu
                cmd = f'powershell "Start-Process \'{app_display_name}\'"'
                subprocess.run(cmd, shell=True, timeout=10)
                return True
                
            return False
            
        except Exception as e:
            print(f"[AppDetector] Ошибка запуска через Start Menu: {e}")
            return False
            
    def get_detected_apps(self) -> Dict[str, Dict]:
        """Получить обнаруженные приложения"""
        return self.detected_apps.copy()
        
    def get_app_history(self) -> List[Dict]:
        """Получить историю приложений"""
        return self.app_history.copy()
        
    def is_app_running(self, app_name: str) -> bool:
        """Проверить, запущено ли приложение"""
        return app_name in self.detected_apps
        
    def get_app_info(self, app_name: str) -> Optional[Dict]:
        """Получить информацию о приложении"""
        return self.detected_apps.get(app_name)
        
    def clear_history(self):
        """Очистить историю"""
        self.app_history.clear()
