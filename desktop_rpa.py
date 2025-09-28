# -*- coding: utf-8 -*-
"""
Desktop RPA - автоматизация рабочих столов и приложений
pyautogui для управления Zoom, Outlook, браузерами и т.д.
"""

import time
import logging
import subprocess
import os
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
import pyautogui
import pygetwindow as gw
import psutil
import pyperclip
from PIL import Image
import pytesseract


@dataclass
class AppWindow:
    """Информация об окне приложения"""
    title: str
    process_name: str
    hwnd: Any
    rect: Tuple[int, int, int, int]  # left, top, right, bottom


@dataclass
class AutomationTask:
    """Задача автоматизации"""
    name: str
    app_name: str
    actions: List[Dict[str, Any]]
    timeout: int = 30
    retries: int = 3


class DesktopRPA:
    """
    Desktop RPA для автоматизации приложений
    """

    def __init__(self, confidence: float = 0.8, pause: float = 0.5):
        """
        Args:
            confidence: Уверенность для поиска изображений
            pause: Пауза между действиями (сек)
        """
        self.confidence = confidence
        self.pause = pause

        self.logger = logging.getLogger("DesktopRPA")

        # Настройки pyautogui
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = pause

        # Кэш окон
        self.window_cache = {}

        # Настройки приложений
        self.app_configs = {
            "zoom": {
                "process_names": ["zoom.exe", "Zoom.exe"],
                "window_titles": ["Zoom", "Zoom Meeting"],
                "actions": {
                    "mute_mic": {"type": "hotkey", "keys": ["alt", "a"]},
                    "mute_video": {"type": "hotkey", "keys": ["alt", "v"]},
                    "share_screen": {"type": "hotkey", "keys": ["alt", "s"]},
                    "leave_meeting": {"type": "hotkey", "keys": ["alt", "q"]}
                }
            },
            "outlook": {
                "process_names": ["outlook.exe", "OUTLOOK.EXE"],
                "window_titles": ["Outlook", "Microsoft Outlook"],
                "actions": {
                    "new_email": {"type": "hotkey", "keys": ["ctrl", "n"]},
                    "reply": {"type": "hotkey", "keys": ["ctrl", "r"]},
                    "forward": {"type": "hotkey", "keys": ["ctrl", "f"]},
                    "send": {"type": "hotkey", "keys": ["ctrl", "enter"]}
                }
            },
            "telegram": {
                "process_names": ["telegram.exe", "Telegram.exe"],
                "window_titles": ["Telegram"],
                "actions": {
                    "new_chat": {"type": "hotkey", "keys": ["ctrl", "n"]},
                    "search": {"type": "hotkey", "keys": ["ctrl", "f"]},
                    "send": {"type": "hotkey", "keys": ["enter"]}
                }
            },
            "chrome": {
                "process_names": ["chrome.exe", "chromium.exe"],
                "window_titles": ["Google Chrome", "Chrome"],
                "actions": {
                    "new_tab": {"type": "hotkey", "keys": ["ctrl", "t"]},
                    "close_tab": {"type": "hotkey", "keys": ["ctrl", "w"]},
                    "refresh": {"type": "hotkey", "keys": ["f5"]},
                    "dev_tools": {"type": "hotkey", "keys": ["f12"]}
                }
            }
        }

        # История действий
        self.action_history = []

    def find_app_window(self, app_name: str) -> Optional[AppWindow]:
        """
        Поиск окна приложения
        """
        try:
            config = self.app_configs.get(app_name.lower())
            if not config:
                return None

            # Сначала ищем по названию процесса
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() in [p.lower() for p in config['process_names']]:
                    try:
                        windows = gw.getWindowsWithTitle('')  # Получаем все окна
                        for window in windows:
                            if any(title.lower() in window.title.lower() for title in config['window_titles']):
                                return AppWindow(
                                    title=window.title,
                                    process_name=proc.info['name'],
                                    hwnd=window._hWnd,
                                    rect=(window.left, window.top, window.right, window.bottom)
                                )
                    except Exception as e:
                        self.logger.warning(f"Error finding window for {app_name}: {e}")

            return None

        except Exception as e:
            self.logger.error(f"Failed to find app window {app_name}: {e}")
            return None

    def activate_window(self, app_window: AppWindow) -> bool:
        """
        Активация окна приложения
        """
        try:
            window = gw.Window(app_window.hwnd)
            window.activate()
            time.sleep(0.5)  # Ждем активации
            return True
        except Exception as e:
            self.logger.error(f"Failed to activate window: {e}")
            return False

    def execute_action(self, app_name: str, action_name: str) -> bool:
        """
        Выполнение действия в приложении
        """
        try:
            # Находим окно
            app_window = self.find_app_window(app_name)
            if not app_window:
                self.logger.warning(f"Window not found for {app_name}")
                return False

            # Активируем окно
            if not self.activate_window(app_window):
                return False

            # Получаем конфиг действия
            config = self.app_configs.get(app_name.lower())
            if not config:
                return False

            action_config = config['actions'].get(action_name)
            if not action_config:
                return False

            # Выполняем действие
            action_type = action_config['type']

            if action_type == "hotkey":
                keys = action_config['keys']
                pyautogui.hotkey(*keys)
                self.logger.info(f"Executed hotkey {keys} in {app_name}")

            elif action_type == "click":
                x, y = action_config.get('position', (0, 0))
                pyautogui.click(x, y)
                self.logger.info(f"Clicked at ({x}, {y}) in {app_name}")

            elif action_type == "type_text":
                text = action_config.get('text', '')
                pyautogui.typewrite(text, interval=0.05)
                self.logger.info(f"Typed text in {app_name}")

            # Логируем действие
            self.log_action(f"{app_name}.{action_name}", {"type": action_type})

            return True

        except Exception as e:
            self.logger.error(f"Failed to execute action {action_name} in {app_name}: {e}")
            return False

    def zoom_control(self, action: str) -> bool:
        """
        Управление Zoom
        """
        actions = {
            "mute": "mute_mic",
            "unmute": "mute_mic",  # Тот же хоткей
            "video_off": "mute_video",
            "video_on": "mute_video",  # Тот же хоткей
            "share_screen": "share_screen",
            "leave": "leave_meeting"
        }

        if action in actions:
            return self.execute_action("zoom", actions[action])
        return False

    def outlook_email(self, to: str, subject: str, body: str, attachments: List[str] = None) -> bool:
        """
        Отправка email через Outlook
        """
        try:
            # Активируем Outlook
            if not self.execute_action("outlook", "new_email"):
                return False

            time.sleep(1)

            # Заполняем получателя
            pyautogui.typewrite(to, interval=0.05)
            time.sleep(0.5)
            pyautogui.press('tab')

            # Тема
            pyautogui.typewrite(subject, interval=0.05)
            time.sleep(0.5)
            pyautogui.press('tab')

            # Тело письма
            pyautogui.typewrite(body, interval=0.05)
            time.sleep(0.5)

            # Прикрепляем файлы если есть
            if attachments:
                for attachment in attachments:
                    # TODO: реализовать прикрепление файлов
                    pass

            # Отправляем
            time.sleep(1)
            if self.execute_action("outlook", "send"):
                self.logger.info(f"Email sent to {to}")
                return True

            return False

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False

    def telegram_message(self, contact: str, message: str) -> bool:
        """
        Отправка сообщения в Telegram
        """
        try:
            # Активируем Telegram
            if not self.execute_action("telegram", "search"):
                return False

            time.sleep(1)

            # Ищем контакт
            pyautogui.typewrite(contact, interval=0.05)
            time.sleep(1)
            pyautogui.press('enter')

            time.sleep(1)

            # Пишем сообщение
            pyautogui.typewrite(message, interval=0.05)
            time.sleep(0.5)

            # Отправляем
            pyautogui.press('enter')

            self.logger.info(f"Message sent to {contact} in Telegram")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            return False

    def browser_automation(self, url: str = None, search_query: str = None) -> bool:
        """
        Автоматизация браузера
        """
        try:
            # Открываем новую вкладку
            if not self.execute_action("chrome", "new_tab"):
                return False

            time.sleep(1)

            if url:
                # Переходим по URL
                pyautogui.typewrite(url, interval=0.05)
                pyautogui.press('enter')
            elif search_query:
                # Ищем в Google
                pyautogui.typewrite(search_query, interval=0.05)
                pyautogui.press('enter')

            time.sleep(2)
            self.logger.info(f"Browser automation completed: {url or search_query}")
            return True

        except Exception as e:
            self.logger.error(f"Browser automation failed: {e}")
            return False

    def take_screenshot(self, region: Tuple[int, int, int, int] = None) -> Optional[Image.Image]:
        """
        Скриншот экрана или области
        """
        try:
            screenshot = pyautogui.screenshot(region=region)
            self.logger.info("Screenshot taken")
            return screenshot
        except Exception as e:
            self.logger.error(f"Screenshot failed: {e}")
            return None

    def find_image_on_screen(self, image_path: str, confidence: float = None) -> Optional[Tuple[int, int]]:
        """
        Поиск изображения на экране
        """
        try:
            if confidence is None:
                confidence = self.confidence

            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                self.logger.info(f"Image found at {center}")
                return center
            return None
        except Exception as e:
            self.logger.error(f"Image search failed: {e}")
            return None

    def click_on_image(self, image_path: str) -> bool:
        """
        Клик по изображению на экране
        """
        try:
            location = self.find_image_on_screen(image_path)
            if location:
                pyautogui.click(location)
                self.logger.info("Clicked on image")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Click on image failed: {e}")
            return False

    def extract_text_from_screen(self, region: Tuple[int, int, int, int] = None,
                                lang: str = 'rus+eng') -> Optional[str]:
        """
        OCR - извлечение текста с экрана
        """
        try:
            screenshot = self.take_screenshot(region)
            if screenshot:
                text = pytesseract.image_to_string(screenshot, lang=lang)
                self.logger.info(f"OCR extracted text: {len(text)} chars")
                return text.strip()
            return None
        except Exception as e:
            self.logger.error(f"OCR failed: {e}")
            return None

    def get_running_apps(self) -> List[Dict[str, Any]]:
        """
        Получение списка запущенных приложений
        """
        try:
            apps = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    apps.append({
                        'pid': proc.info['pid'],
                        'name': proc.info['name'],
                        'cpu': proc.info['cpu_percent'],
                        'memory': proc.info['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return apps
        except Exception as e:
            self.logger.error(f"Failed to get running apps: {e}")
            return []

    def launch_application(self, app_path: str, arguments: List[str] = None) -> bool:
        """
        Запуск приложения
        """
        try:
            if arguments:
                subprocess.Popen([app_path] + arguments)
            else:
                subprocess.Popen(app_path)

            self.logger.info(f"Application launched: {app_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to launch application: {e}")
            return False

    def close_application(self, app_name: str) -> bool:
        """
        Закрытие приложения
        """
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if app_name.lower() in proc.info['name'].lower():
                    proc.kill()
                    self.logger.info(f"Application closed: {app_name}")
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to close application: {e}")
            return False

    def execute_task(self, task: AutomationTask) -> bool:
        """
        Выполнение комплексной задачи автоматизации
        """
        try:
            self.logger.info(f"Starting automation task: {task.name}")

            for attempt in range(task.retries):
                try:
                    # Активируем приложение
                    app_window = self.find_app_window(task.app_name)
                    if not app_window:
                        self.logger.warning(f"App {task.app_name} not found, attempt {attempt + 1}")
                        time.sleep(2)
                        continue

                    if not self.activate_window(app_window):
                        continue

                    # Выполняем действия
                    for action in task.actions:
                        action_type = action['type']

                        if action_type == 'wait':
                            time.sleep(action.get('seconds', 1))

                        elif action_type == 'hotkey':
                            pyautogui.hotkey(*action['keys'])

                        elif action_type == 'click':
                            if 'image' in action:
                                # Клик по изображению
                                if not self.click_on_image(action['image']):
                                    raise Exception(f"Image not found: {action['image']}")
                            else:
                                # Клик по координатам
                                pyautogui.click(action['x'], action['y'])

                        elif action_type == 'type':
                            pyautogui.typewrite(action['text'], interval=0.05)

                        elif action_type == 'scroll':
                            pyautogui.scroll(action.get('clicks', 3))

                        time.sleep(0.5)  # Пауза между действиями

                    self.logger.info(f"Task {task.name} completed successfully")
                    return True

                except Exception as e:
                    self.logger.warning(f"Task attempt {attempt + 1} failed: {e}")
                    time.sleep(1)

            self.logger.error(f"Task {task.name} failed after {task.retries} attempts")
            return False

        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            return False

    def create_zoom_meeting_task(self, meeting_id: str, password: str = None) -> AutomationTask:
        """
        Создание задачи для присоединения к Zoom встрече
        """
        actions = [
            {'type': 'hotkey', 'keys': ['win', 'r']},  # Win + R
            {'type': 'wait', 'seconds': 1},
            {'type': 'type', 'text': 'zoom'},
            {'type': 'wait', 'seconds': 1},
            {'type': 'hotkey', 'keys': ['enter']},
            {'type': 'wait', 'seconds': 3},
            {'type': 'type', 'text': meeting_id},
            {'type': 'wait', 'seconds': 1},
            {'type': 'hotkey', 'keys': ['enter']}
        ]

        if password:
            actions.extend([
                {'type': 'wait', 'seconds': 2},
                {'type': 'type', 'text': password},
                {'type': 'hotkey', 'keys': ['enter']}
            ])

        return AutomationTask(
            name=f"Join Zoom Meeting {meeting_id}",
            app_name="zoom",
            actions=actions,
            timeout=60
        )

    def create_email_task(self, to: str, subject: str, body: str) -> AutomationTask:
        """
        Создание задачи для отправки email
        """
        actions = [
            {'type': 'hotkey', 'keys': ['win', 'r']},  # Запуск Outlook
            {'type': 'wait', 'seconds': 1},
            {'type': 'type', 'text': 'outlook'},
            {'type': 'hotkey', 'keys': ['enter']},
            {'type': 'wait', 'seconds': 5},
            {'type': 'hotkey', 'keys': ['ctrl', 'n']},  # Новое письмо
            {'type': 'wait', 'seconds': 2},
            {'type': 'type', 'text': to},  # Получатель
            {'type': 'hotkey', 'keys': ['tab']},
            {'type': 'type', 'text': subject},  # Тема
            {'type': 'hotkey', 'keys': ['tab']},
            {'type': 'type', 'text': body},  # Тело письма
            {'type': 'wait', 'seconds': 1},
            {'type': 'hotkey', 'keys': ['ctrl', 'enter']}  # Отправить
        ]

        return AutomationTask(
            name=f"Send Email to {to}",
            app_name="outlook",
            actions=actions,
            timeout=30
        )

    def log_action(self, action_name: str, details: Dict[str, Any] = None):
        """
        Логирование действия
        """
        entry = {
            'timestamp': time.time(),
            'action': action_name,
            'details': details or {}
        }
        self.action_history.append(entry)

    def get_action_history(self) -> List[Dict[str, Any]]:
        """
        Получение истории действий
        """
        return self.action_history.copy()

    def clear_history(self):
        """
        Очистка истории
        """
        self.action_history.clear()
        self.logger.info("Action history cleared")

    def set_mouse_speed(self, speed: float):
        """
        Установка скорости мыши (0.0 - 1.0)
        """
        pyautogui.MINIMUM_DURATION = speed
        pyautogui.MINIMUM_SLEEP = speed
        self.logger.info(f"Mouse speed set to {speed}")

    def emergency_stop(self):
        """
        Экстренная остановка всех действий
        """
        try:
            # Двигаем мышь в угол экрана для failsafe
            screen_width, screen_height = pyautogui.size()
            pyautogui.moveTo(0, 0)
            self.logger.info("Emergency stop activated")
        except Exception as e:
            self.logger.error(f"Emergency stop failed: {e}")