# -*- coding: utf-8 -*-
"""
Secrets & Watchdog Module
Управление секретами в Credential Manager, retry/backoff, watchdog
"""

import os
import time
import threading
import json
import psutil
import subprocess
from pathlib import Path
from typing import Dict, Optional, Callable, List, Any
from dataclasses import dataclass
import logging


@dataclass
class RetryConfig:
    """Конфигурация retry логики"""
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True


@dataclass
class WatchdogConfig:
    """Конфигурация watchdog"""
    check_interval: float = 30.0
    restart_delay: float = 5.0
    max_restarts: int = 3
    crash_dump_enabled: bool = False
    log_crashes: bool = True


class SecretsManager:
    """
    Менеджер секретов с поддержкой Windows Credential Manager и .env
    """

    def __init__(self, env_file: str = ".env", use_credential_manager: bool = True):
        """
        Args:
            env_file: Путь к .env файлу
            use_credential_manager: Использовать Windows Credential Manager
        """
        self.env_file = Path(env_file)
        self.use_credential_manager = use_credential_manager
        self.secrets_cache = {}

        # Загружаем секреты при инициализации
        self._load_secrets()

    def _load_secrets(self):
        """Загрузка секретов из всех источников"""
        # Загружаем из .env файла
        self._load_from_env_file()

        # Загружаем из Windows Credential Manager
        if self.use_credential_manager:
            self._load_from_credential_manager()

    def _load_from_env_file(self):
        """Загрузка из .env файла"""
        try:
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                self.secrets_cache[key.strip()] = value.strip()
        except Exception as e:
            print(f"[SecretsManager] Ошибка загрузки .env: {e}")

    def _load_from_credential_manager(self):
        """Загрузка из Windows Credential Manager"""
        try:
            # Используем cmdkey для Windows Credential Manager
            result = subprocess.run(
                ['cmdkey', '/list'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_target = None

                for line in lines:
                    line = line.strip()
                    if line.startswith('Target: '):
                        current_target = line.replace('Target: ', '')
                    elif line.startswith('User: ') and current_target:
                        username = line.replace('User: ', '')
                        # Получаем пароль
                        try:
                            password_result = subprocess.run(
                                ['cmdkey', '/generic', current_target],
                                capture_output=True,
                                text=True,
                                timeout=5
                            )
                            # Парсинг сложный, поэтому просто сохраняем факт наличия
                            self.secrets_cache[f'CRED_{current_target}'] = f'user:{username}'
                        except Exception:
                            pass

        except Exception as e:
            print(f"[SecretsManager] Credential Manager недоступен: {e}")

    def get_secret(self, key: str, default: str = "") -> str:
        """Получение секрета"""
        return self.secrets_cache.get(key, os.environ.get(key, default))

    def set_secret(self, key: str, value: str, persist: bool = True):
        """Установка секрета"""
        self.secrets_cache[key] = value

        if persist:
            # Сохраняем в .env файл
            self._save_to_env_file(key, value)

            # Сохраняем в Credential Manager если это API ключ
            if self.use_credential_manager and any(keyword in key.lower() for keyword in ['api', 'key', 'secret', 'token']):
                self._save_to_credential_manager(key, value)

    def _save_to_env_file(self, key: str, value: str):
        """Сохранение в .env файл"""
        try:
            env_data = {}
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if '=' in line:
                            k, v = line.split('=', 1)
                            env_data[k.strip()] = v.strip()

            env_data[key] = value

            with open(self.env_file, 'w', encoding='utf-8') as f:
                for k, v in env_data.items():
                    f.write(f"{k}={v}\n")

        except Exception as e:
            print(f"[SecretsManager] Ошибка сохранения в .env: {e}")

    def _save_to_credential_manager(self, key: str, value: str):
        """Сохранение в Windows Credential Manager"""
        try:
            # Используем cmdkey для сохранения
            # Для простоты сохраняем как generic credential
            target_name = f"AI_Magistr_{key}"

            # Удаляем старую если есть
            subprocess.run(['cmdkey', '/delete', target_name],
                         capture_output=True, timeout=5)

            # Добавляем новую
            subprocess.run(['cmdkey', '/generic', target_name, '/user', key, '/pass', value],
                         capture_output=True, timeout=5)

        except Exception as e:
            print(f"[SecretsManager] Ошибка сохранения в Credential Manager: {e}")

    def delete_secret(self, key: str):
        """Удаление секрета"""
        if key in self.secrets_cache:
            del self.secrets_cache[key]

        # Удаляем из .env
        if self.env_file.exists():
            env_data = {}
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if '=' in line:
                        k, v = line.split('=', 1)
                        if k.strip() != key:
                            env_data[k.strip()] = v.strip()

            with open(self.env_file, 'w', encoding='utf-8') as f:
                for k, v in env_data.items():
                    f.write(f"{k}={v}\n")

        # Удаляем из Credential Manager
        if self.use_credential_manager:
            try:
                target_name = f"AI_Magistr_{key}"
                subprocess.run(['cmdkey', '/delete', target_name],
                             capture_output=True, timeout=5)
            except Exception:
                pass

    def list_secrets(self) -> List[str]:
        """Список доступных секретов"""
        return list(self.secrets_cache.keys())


class RetryManager:
    """
    Менеджер retry логики с exponential backoff
    """

    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()

    def execute_with_retry(self, func: Callable, *args, **kwargs) -> Any:
        """Выполнение функции с retry"""
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                if attempt < self.config.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    print(f"[RetryManager] Попытка {attempt + 1} failed: {e}. Повтор через {delay:.1f} сек")
                    time.sleep(delay)
                else:
                    print(f"[RetryManager] Все {self.config.max_attempts} попыток исчерпаны")

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Расчет задержки с exponential backoff"""
        delay = self.config.initial_delay * (self.config.backoff_factor ** attempt)

        # Ограничиваем максимальную задержку
        delay = min(delay, self.config.max_delay)

        # Добавляем jitter если включен
        if self.config.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay


class Watchdog:
    """
    Watchdog для мониторинга и перезапуска процессов
    """

    def __init__(self, config: WatchdogConfig = None, on_restart: Optional[Callable] = None):
        """
        Args:
            config: Конфигурация watchdog
            on_restart: Callback при перезапуске процесса
        """
        self.config = config or WatchdogConfig()
        self.on_restart = on_restart

        self.monitored_processes = {}  # pid -> process_info
        self.restart_counts = {}  # name -> count
        self.is_monitoring = False
        self.monitor_thread = None

        # Настройка логирования crashes
        if self.config.log_crashes:
            logging.basicConfig(
                filename='crash_logs.txt',
                level=logging.ERROR,
                format='%(asctime)s - %(levelname)s - %(message)s'
            )

    def add_process(self, name: str, pid: int, restart_command: Optional[List[str]] = None):
        """Добавление процесса для мониторинга"""
        self.monitored_processes[pid] = {
            'name': name,
            'pid': pid,
            'restart_command': restart_command,
            'last_check': time.time(),
            'status': 'running'
        }

    def remove_process(self, pid: int):
        """Удаление процесса из мониторинга"""
        if pid in self.monitored_processes:
            del self.monitored_processes[pid]

    def start_monitoring(self):
        """Запуск мониторинга"""
        if self.is_monitoring:
            return

        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1.0)

    def _monitor_worker(self):
        """Поток мониторинга процессов"""
        while self.is_monitoring:
            try:
                current_time = time.time()

                # Проверяем каждый процесс
                for pid, proc_info in list(self.monitored_processes.items()):
                    if current_time - proc_info['last_check'] < self.config.check_interval:
                        continue

                    proc_info['last_check'] = current_time

                    # Проверяем, жив ли процесс
                    if not self._is_process_alive(pid):
                        print(f"[Watchdog] Процесс {proc_info['name']} (PID: {pid}) умер")

                        # Логируем crash
                        if self.config.log_crashes:
                            logging.error(f"Process {proc_info['name']} (PID: {pid}) crashed")

                        # Создаем crash dump если включено
                        if self.config.crash_dump_enabled:
                            self._create_crash_dump(pid, proc_info)

                        # Пытаемся перезапустить
                        self._restart_process(proc_info)

                        # Удаляем из мониторинга
                        del self.monitored_processes[pid]

                    else:
                        proc_info['status'] = 'running'

            except Exception as e:
                print(f"[Watchdog] Ошибка мониторинга: {e}")

            time.sleep(self.config.check_interval)

    def _is_process_alive(self, pid: int) -> bool:
        """Проверка, жив ли процесс"""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def _restart_process(self, proc_info: Dict):
        """Перезапуск процесса"""
        name = proc_info['name']
        restart_cmd = proc_info.get('restart_command')

        if not restart_cmd:
            print(f"[Watchdog] Нет команды перезапуска для {name}")
            return

        # Проверяем лимит перезапусков
        restart_count = self.restart_counts.get(name, 0)
        if restart_count >= self.config.max_restarts:
            print(f"[Watchdog] Превышен лимит перезапусков для {name}")
            return

        # Ждем перед перезапуском
        time.sleep(self.config.restart_delay)

        try:
            print(f"[Watchdog] Перезапускаю {name}...")
            result = subprocess.Popen(restart_cmd)

            # Добавляем новый процесс в мониторинг
            self.add_process(name, result.pid, restart_cmd)

            # Увеличиваем счетчик
            self.restart_counts[name] = restart_count + 1

            # Callback
            if self.on_restart:
                self.on_restart(name, result.pid)

            print(f"[Watchdog] {name} перезапущен (PID: {result.pid})")

        except Exception as e:
            print(f"[Watchdog] Ошибка перезапуска {name}: {e}")

    def _create_crash_dump(self, pid: int, proc_info: Dict):
        """Создание crash dump"""
        try:
            dump_file = f"crash_dump_{proc_info['name']}_{int(time.time())}.dmp"

            # Для Windows используем procdump или аналог
            # Здесь упрощенная версия - просто логируем состояние
            with open(dump_file, 'w') as f:
                f.write(f"Crash dump for {proc_info['name']} (PID: {pid})\n")
                f.write(f"Time: {time.ctime()}\n")
                f.write(f"Process info: {json.dumps(proc_info, indent=2)}\n")

            print(f"[Watchdog] Crash dump создан: {dump_file}")

        except Exception as e:
            print(f"[Watchdog] Ошибка создания crash dump: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Получение статуса watchdog"""
        return {
            'is_monitoring': self.is_monitoring,
            'monitored_processes': len(self.monitored_processes),
            'restart_counts': self.restart_counts.copy(),
            'config': {
                'check_interval': self.config.check_interval,
                'max_restarts': self.config.max_restarts
            }
        }


class SecretsWatchdogManager:
    """
    Объединенный менеджер секретов и watchdog
    """

    def __init__(self,
                 secrets_config: Dict = None,
                 retry_config: RetryConfig = None,
                 watchdog_config: WatchdogConfig = None):
        """
        Args:
            secrets_config: Конфигурация секретов
            retry_config: Конфигурация retry
            watchdog_config: Конфигурация watchdog
        """
        secrets_config = secrets_config or {}
        self.secrets_manager = SecretsManager(**secrets_config)
        self.retry_manager = RetryManager(retry_config)
        self.watchdog = Watchdog(watchdog_config, self._on_process_restart)

    def _on_process_restart(self, name: str, new_pid: int):
        """Callback при перезапуске процесса"""
        print(f"[SecretsWatchdog] Процесс {name} перезапущен с PID {new_pid}")

    def safe_api_call(self, api_func: Callable, *args, **kwargs) -> Any:
        """Безопасный API вызов с retry"""
        return self.retry_manager.execute_with_retry(api_func, *args, **kwargs)

    def get_secret(self, key: str, default: str = "") -> str:
        """Получение секрета"""
        return self.secrets_manager.get_secret(key, default)

    def set_secret(self, key: str, value: str, persist: bool = True):
        """Установка секрета"""
        self.secrets_manager.set_secret(key, value, persist)

    def monitor_process(self, name: str, pid: int, restart_command: Optional[List[str]] = None):
        """Добавление процесса в мониторинг"""
        self.watchdog.add_process(name, pid, restart_command)

    def start_monitoring(self):
        """Запуск мониторинга"""
        self.watchdog.start_monitoring()

    def stop_monitoring(self):
        """Остановка мониторинга"""
        self.watchdog.stop_monitoring()

    def get_status(self) -> Dict[str, Any]:
        """Получение общего статуса"""
        return {
            'secrets': {
                'available_secrets': len(self.secrets_manager.list_secrets())
            },
            'retry': {
                'max_attempts': self.retry_manager.config.max_attempts,
                'backoff_factor': self.retry_manager.config.backoff_factor
            },
            'watchdog': self.watchdog.get_status()
        }
