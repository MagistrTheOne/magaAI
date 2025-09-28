# -*- coding: utf-8 -*-
"""
Orchestrator - Автозапуск и мониторинг стеков
Управляет: ghost_assistant_win.py, brain, vision, rag
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import psutil
import requests
from loguru import logger
import sounddevice as sd


class HealthChecker:
    """Проверка здоровья системы"""
    
    def __init__(self):
        self.checks = {}
    
    def check_ffmpeg(self) -> bool:
        """Проверка FFmpeg"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def check_vb_cable(self) -> bool:
        """Проверка VB-CABLE"""
        try:
            devices = sd.query_devices()
            for device in devices:
                if "cable" in device["name"].lower():
                    return True
            return False
        except:
            return False
    
    def check_audio_devices(self) -> Dict[str, bool]:
        """Проверка аудио устройств"""
        result = {"output": False, "input": False, "loopback": False}
        
        try:
            devices = sd.query_devices()
            for device in devices:
                if device["max_output_channels"] > 0:
                    result["output"] = True
                if device["max_input_channels"] > 0:
                    result["input"] = True
                if "loopback" in device["name"].lower():
                    result["loopback"] = True
        except:
            pass
        
        return result
    
    def check_vpn(self) -> bool:
        """Проверка VPN (пинг доменов)"""
        test_domains = ["google.com", "github.com", "gigachat.devices.sberbank.ru"]
        
        for domain in test_domains:
            try:
                response = requests.get(f"https://{domain}", timeout=5)
                if response.status_code == 200:
                    return True
            except:
                continue
        return False
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Запуск всех проверок"""
        checks = {
            "ffmpeg": self.check_ffmpeg(),
            "vb_cable": self.check_vb_cable(),
            "audio": self.check_audio_devices(),
            "vpn": self.check_vpn(),
            "timestamp": datetime.now().isoformat()
        }
        
        # Общий статус
        checks["overall"] = all([
            checks["ffmpeg"],
            checks["vb_cable"],
            checks["audio"]["output"],
            checks["audio"]["input"]
        ])
        
        return checks


class ProcessManager:
    """Управление процессами"""
    
    def __init__(self):
        self.processes = {}
        self.scripts = {
            "ghost_assistant": "ghost_assistant_win.py",
            "voice_trigger": "voice_trigger.py",
            "screen_scanner": "computer_vision.py",
            "job_search": "job_search_api.py"
        }
    
    def start_script(self, name: str, script_path: str, **kwargs) -> bool:
        """Запуск скрипта"""
        try:
            if name in self.processes:
                logger.warning(f"Процесс {name} уже запущен")
                return True
            
            # Запускаем процесс
            cmd = ["python", script_path]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **kwargs
            )
            
            self.processes[name] = {
                "process": process,
                "script": script_path,
                "started_at": datetime.now(),
                "status": "running"
            }
            
            logger.info(f"Запущен процесс: {name} ({script_path})")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка запуска {name}: {e}")
            return False
    
    def stop_script(self, name: str) -> bool:
        """Остановка скрипта"""
        try:
            if name not in self.processes:
                logger.warning(f"Процесс {name} не найден")
                return True
            
            process_info = self.processes[name]
            process = process_info["process"]
            
            # Мягкая остановка
            process.terminate()
            process.wait(timeout=5)
            
            # Принудительная остановка если нужно
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)
            
            del self.processes[name]
            logger.info(f"Остановлен процесс: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка остановки {name}: {e}")
            return False
    
    def get_process_status(self, name: str) -> Optional[Dict]:
        """Получение статуса процесса"""
        if name not in self.processes:
            return None
        
        process_info = self.processes[name]
        process = process_info["process"]
        
        return {
            "name": name,
            "pid": process.pid,
            "status": "running" if process.poll() is None else "stopped",
            "started_at": process_info["started_at"],
            "uptime": (datetime.now() - process_info["started_at"]).total_seconds()
        }
    
    def get_all_status(self) -> Dict[str, Dict]:
        """Получение статуса всех процессов"""
        return {name: self.get_process_status(name) for name in self.processes.keys()}
    
    def cleanup_dead_processes(self):
        """Очистка мертвых процессов"""
        dead_processes = []
        
        for name, process_info in self.processes.items():
            process = process_info["process"]
            if process.poll() is not None:
                dead_processes.append(name)
        
        for name in dead_processes:
            logger.warning(f"Процесс {name} завершился")
            del self.processes[name]


class Orchestrator:
    """Главный оркестратор системы"""
    
    def __init__(self, config_file: str = "orchestrator_config.json"):
        self.config_file = config_file
        self.health_checker = HealthChecker()
        self.process_manager = ProcessManager()
        
        # Состояние
        self.is_running = False
        self.monitor_thread = None
        self.stop_event = threading.Event()
        
        # Настройки
        self.monitor_interval = 10.0  # секунды
        self.auto_restart = True
        self.health_check_interval = 30.0  # секунды
        
        # Логи
        self.setup_logging()
        
        logger.info("Orchestrator инициализирован")
    
    def setup_logging(self):
        """Настройка логирования"""
        # Создаем папку для логов
        os.makedirs("logs", exist_ok=True)
        
        # Настраиваем loguru
        logger.add(
            "logs/orchestrator_{time:YYYY-MM-DD}.log",
            rotation="1 day",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def start_system(self) -> bool:
        """Запуск всей системы"""
        logger.info("🚀 Запуск системы...")
        
        # Проверяем здоровье
        health = self.health_checker.run_all_checks()
        if not health["overall"]:
            logger.error("❌ Система не готова к запуску")
            logger.error(f"Health check: {health}")
            return False
        
        logger.info("✅ Health check пройден")
        
        # Запускаем основные процессы
        success = True
        
        # 1. Ghost Assistant (основной)
        if not self.process_manager.start_script("ghost_assistant", "ghost_assistant_win.py"):
            success = False
        
        # 2. Voice Trigger (опционально)
        if os.path.exists("voice_trigger.py"):
            if not self.process_manager.start_script("voice_trigger", "voice_trigger.py"):
                logger.warning("Voice Trigger не запущен")
        
        # 3. Screen Scanner (опционально)
        if os.path.exists("computer_vision.py"):
            if not self.process_manager.start_script("screen_scanner", "computer_vision.py"):
                logger.warning("Screen Scanner не запущен")
        
        if success:
            logger.info("🎉 Система запущена успешно!")
            self.start_monitoring()
        else:
            logger.error("❌ Ошибка запуска системы")
        
        return success
    
    def stop_system(self):
        """Остановка системы"""
        logger.info("🛑 Остановка системы...")
        
        self.stop_event.set()
        
        # Останавливаем мониторинг
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5.0)
        
        # Останавливаем все процессы
        for name in list(self.process_manager.processes.keys()):
            self.process_manager.stop_script(name)
        
        self.is_running = False
        logger.info("✅ Система остановлена")
    
    def start_monitoring(self):
        """Запуск мониторинга"""
        if self.is_running:
            return
        
        self.is_running = True
        self.stop_event.clear()
        
        self.monitor_thread = threading.Thread(target=self._monitor_worker, daemon=True)
        self.monitor_thread.start()
        
        logger.info("📊 Мониторинг запущен")
    
    def _monitor_worker(self):
        """Рабочий поток мониторинга"""
        last_health_check = 0
        
        while not self.stop_event.is_set():
            try:
                # Очищаем мертвые процессы
                self.process_manager.cleanup_dead_processes()
                
                # Проверяем здоровье системы
                current_time = time.time()
                if current_time - last_health_check > self.health_check_interval:
                    health = self.health_checker.run_all_checks()
                    if not health["overall"]:
                        logger.warning("⚠️ Проблемы с системой обнаружены")
                        logger.warning(f"Health: {health}")
                    
                    last_health_check = current_time
                
                # Автоперезапуск процессов
                if self.auto_restart:
                    self._check_and_restart_processes()
                
                time.sleep(self.monitor_interval)
                
            except Exception as e:
                logger.error(f"Ошибка в мониторинге: {e}")
                time.sleep(5)
    
    def _check_and_restart_processes(self):
        """Проверка и перезапуск процессов"""
        critical_processes = ["ghost_assistant"]
        
        for name in critical_processes:
            status = self.process_manager.get_process_status(name)
            if status and status["status"] == "stopped":
                logger.warning(f"Критический процесс {name} остановлен, перезапускаем...")
                
                # Останавливаем если еще в списке
                if name in self.process_manager.processes:
                    self.process_manager.stop_script(name)
                
                # Перезапускаем
                script_path = self.process_manager.scripts.get(name)
                if script_path:
                    self.process_manager.start_script(name, script_path)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Получение статуса системы"""
        health = self.health_checker.run_all_checks()
        processes = self.process_manager.get_all_status()
        
        return {
            "is_running": self.is_running,
            "health": health,
            "processes": processes,
            "timestamp": datetime.now().isoformat()
        }
    
    def restart_process(self, name: str) -> bool:
        """Перезапуск конкретного процесса"""
        logger.info(f"🔄 Перезапуск процесса: {name}")
        
        # Останавливаем
        self.process_manager.stop_script(name)
        
        # Запускаем заново
        script_path = self.process_manager.scripts.get(name)
        if script_path:
            return self.process_manager.start_script(name, script_path)
        
        return False


# =============== ТЕСТИРОВАНИЕ ===============

def test_orchestrator():
    """Тестирование Orchestrator"""
    print("🧪 Тестирование Orchestrator...")
    
    orchestrator = Orchestrator()
    
    # Проверяем здоровье
    health = orchestrator.health_checker.run_all_checks()
    print(f"Health check: {health}")
    
    if health["overall"]:
        print("✅ Система готова к запуску")
        
        # Запускаем систему
        if orchestrator.start_system():
            print("🎉 Система запущена!")
            
            # Показываем статус
            status = orchestrator.get_system_status()
            print(f"Статус: {status}")
            
            # Ждем
            print("⏳ Ожидание 10 секунд...")
            time.sleep(10)
            
            # Останавливаем
            orchestrator.stop_system()
            print("🛑 Система остановлена")
        else:
            print("❌ Ошибка запуска системы")
    else:
        print("❌ Система не готова")


if __name__ == "__main__":
    test_orchestrator()
