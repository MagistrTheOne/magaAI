"""
Автономный агент для фоновой работы AI-Maga.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import random

logger = logging.getLogger(__name__)


class AutonomousAgent:
    """Автономный агент для фоновых задач"""

    def __init__(self):
        self.tasks = []
        self.is_running = False
        self.task_scheduler = None
        self.scheduled_tasks = []
        self.check_interval = 300  # 5 минут по умолчанию

    async def start(self):
        """Запустить автономного агента"""
        if self.is_running:
            return

        # Получаем интервал из настроек
        from app.settings import settings
        if hasattr(settings, 'autonomous_check_interval'):
            self.check_interval = settings.autonomous_check_interval

        self.is_running = True
        self.task_scheduler = asyncio.create_task(self._run_scheduler())
        logger.info(f"Автономный агент запущен (интервал: {self.check_interval}с)")

    async def stop(self):
        """Остановить автономного агента"""
        self.is_running = False
        if self.task_scheduler:
            self.task_scheduler.cancel()
            try:
                await self.task_scheduler
            except asyncio.CancelledError:
                logger.debug("Автономный агент был остановлен")
        logger.info("Автономный агент остановлен")

    async def _run_scheduler(self):
        """Основной цикл планировщика задач"""
        try:
            while self.is_running:
                await self._check_scheduled_tasks()
                await self._perform_maintenance_tasks()
                await self._learn_from_patterns()

                # Ждем до следующей проверки
                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info("Планировщик задач остановлен")
        except Exception as e:
            logger.error(f"Ошибка в планировщике задач: {e}")

    async def _check_scheduled_tasks(self):
        """Проверить запланированные задачи"""
        current_time = datetime.now()

        # Примеры задач (в реальности будут из базы данных)
        scheduled_tasks = [
            {
                'id': 'daily_briefing',
                'time': '08:00',
                'action': self._send_daily_briefing,
                'enabled': True
            },
            {
                'id': 'health_check',
                'time': '12:00',
                'action': self._perform_health_check,
                'enabled': True
            },
            {
                'id': 'system_monitor',
                'interval_minutes': 60,
                'action': self._monitor_system,
                'enabled': True,
                'last_run': None
            }
        ]

        for task in scheduled_tasks:
            if not task.get('enabled', False):
                continue

            should_run = False

            if 'time' in task:
                # Проверка по времени
                task_time = datetime.strptime(task['time'], '%H:%M').time()
                if current_time.time().hour == task_time.hour and current_time.time().minute == task_time.minute:
                    should_run = True

            elif 'interval_minutes' in task:
                # Проверка по интервалу
                last_run = task.get('last_run')
                if not last_run or (current_time - last_run).total_seconds() >= task['interval_minutes'] * 60:
                    should_run = True
                    task['last_run'] = current_time

            if should_run:
                try:
                    await task['action']()
                    logger.info(f"Автономная задача выполнена: {task['id']}")
                except Exception as e:
                    logger.error(f"Ошибка выполнения автономной задачи {task['id']}: {e}")

    async def _send_daily_briefing(self):
        """Отправить ежедневный брифинг"""
        # Интеграция с daily_focus сервисом
        try:
            from services.daily_focus import DailyFocus

            focus_service = DailyFocus()
            briefing = await focus_service.generate_briefing()

            # Отправить в Telegram (нужен user_id)
            # await send_telegram_message(user_id, briefing)

            logger.info("Ежедневный брифинг отправлен")
        except Exception as e:
            logger.warning(f"Не удалось отправить ежедневный брифинг: {e}")

    async def _perform_health_check(self):
        """Выполнить проверку здоровья"""
        try:
            from services.health_nudges import HealthNudges

            health_service = HealthNudges()
            health_data = await health_service.get_current_health()

            # Анализ и рекомендации
            recommendations = await self._analyze_health_data(health_data)

            # Отправить рекомендации
            logger.info("Проверка здоровья выполнена")
        except Exception as e:
            logger.warning(f"Не удалось выполнить проверку здоровья: {e}")

    async def _monitor_system(self):
        """Мониторинг системы"""
        try:
            from app.services.os_controller import OSController

            os_controller = OSController()
            system_info = await os_controller.get_system_info()

            # Анализ системных метрик
            if system_info['success']:
                await self._analyze_system_metrics(system_info['system_info'])

            logger.info("Мониторинг системы выполнен")
        except Exception as e:
            logger.warning(f"Не удалось выполнить мониторинг системы: {e}")

    async def _perform_maintenance_tasks(self):
        """Выполнить задачи обслуживания"""
        # Очистка кэша
        await self._cleanup_cache()

        # Обновление индексов
        await self._update_indexes()

        # Проверка обновлений
        await self._check_updates()

    async def _learn_from_patterns(self):
        """Обучение на паттернах использования"""
        try:
            # Анализ логов использования
            logger.info("Анализ паттернов использования...")
            # Здесь будет анализ данных и обновление предпочтений
        except Exception as e:
            logger.error(f"Ошибка анализа паттернов: {e}")

    async def _analyze_health_data(self, health_data: Dict) -> str:
        """Анализ данных здоровья"""
        try:
            # AI анализ паттернов здоровья
            logger.info("Анализ данных здоровья...")
            return "Рекомендации по здоровью на основе анализа"
        except Exception as e:
            logger.error(f"Ошибка анализа здоровья: {e}")
            return "Не удалось проанализировать данные здоровья"

    async def _analyze_system_metrics(self, metrics: Dict):
        """Анализ системных метрик"""
        try:
            # Проверка на проблемы
            cpu_usage = metrics.get('cpu_percent', 0)
            memory_usage = metrics.get('memory_percent', 0)
            
            if cpu_usage > 80:
                logger.warning(f"Высокая нагрузка CPU: {cpu_usage}%")
            if memory_usage > 90:
                logger.warning(f"Высокое использование памяти: {memory_usage}%")
                
        except Exception as e:
            logger.error(f"Ошибка анализа метрик: {e}")

    async def _cleanup_cache(self):
        """Очистка кэша"""
        try:
            import os
            import glob
            from datetime import datetime, timedelta
            
            # Очистка временных файлов старше 7 дней
            temp_dir = "temp"
            if os.path.exists(temp_dir):
                cutoff_time = datetime.now() - timedelta(days=7)
                for file_path in glob.glob(f"{temp_dir}/*"):
                    if os.path.getmtime(file_path) < cutoff_time.timestamp():
                        os.remove(file_path)
                        logger.info(f"Удален старый файл: {file_path}")
                        
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")

    async def _update_indexes(self):
        """Обновление индексов"""
        try:
            # Переиндексация данных
            logger.info("Обновление индексов...")
            # Здесь будет логика переиндексации
        except Exception as e:
            logger.error(f"Ошибка обновления индексов: {e}")

    async def _check_updates(self):
        """Проверка обновлений"""
        try:
            # Проверка версий компонентов
            logger.info("Проверка обновлений компонентов...")
            # Здесь будет проверка версий и доступных обновлений
        except Exception as e:
            logger.error(f"Ошибка проверки обновлений: {e}")

    def add_scheduled_task(self, task_id: str, time: str, action: Callable):
        """Добавить запланированную задачу"""
        self.scheduled_tasks.append({
            'id': task_id,
            'time': time,
            'action': action,
            'enabled': True,
            'last_run': None
        })
        logger.info(f"Добавлена запланированная задача: {task_id} в {time}")

    def remove_scheduled_task(self, task_id: str):
        """Удалить запланированную задачу"""
        self.scheduled_tasks = [t for t in self.scheduled_tasks if t['id'] != task_id]
        logger.info(f"Удалена запланированная задача: {task_id}")

    def enable_task(self, task_id: str):
        """Включить задачу"""
        for task in self.scheduled_tasks:
            if task['id'] == task_id:
                task['enabled'] = True
                logger.info(f"Задача включена: {task_id}")
                break

    def disable_task(self, task_id: str):
        """Отключить задачу"""
        for task in self.scheduled_tasks:
            if task['id'] == task_id:
                task['enabled'] = False
                logger.info(f"Задача отключена: {task_id}")
                break

    def get_status(self) -> Dict:
        """Получить статус агента"""
        return {
            'running': self.is_running,
            'scheduled_tasks': len(self.scheduled_tasks),
            'enabled_tasks': len([t for t in self.scheduled_tasks if t['enabled']]),
            'active_tasks': len(asyncio.all_tasks()) if self.is_running else 0,
            'check_interval': self.check_interval
        }


# Глобальный экземпляр автономного агента
autonomous_agent = AutonomousAgent()
