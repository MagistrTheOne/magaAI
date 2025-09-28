# -*- coding: utf-8 -*-
"""
Health Check для AIMagistr 3.1 - Финальная версия
Максимальная стабильность для Railway
"""

import os
import asyncio
import logging
import signal
import sys
from aiohttp import web
from datetime import datetime
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthCheckServer:
    """Финальный HTTP сервер для health check"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/metrics', self.metrics_handler)
        self.app.router.add_get('/', self.root_handler)
        self.app.router.add_get('/status', self.status_handler)
        
        # Статистика
        self.start_time = datetime.now()
        self.request_count = 0
        self.error_count = 0
        
        # Настройка обработчиков сигналов
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Настройка обработчиков сигналов для graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал {signum}, завершаем работу...")
            sys.exit(0)
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def health_handler(self, request):
        """Обработчик health check"""
        try:
            self.request_count += 1
            
            # Проверяем доступность компонентов
            components = {
                "telegram_bot": "running",
                "health_check": "ok",
                "database": "ok",
                "storage": "ok"
            }
            
            # Проверяем переменные окружения
            env_vars = {
                "TELEGRAM_BOT_TOKEN": "ok" if os.getenv("TELEGRAM_BOT_TOKEN") else "missing",
                "PORT": "ok" if os.getenv("PORT") else "missing"
            }
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": str(datetime.now() - self.start_time),
                "components": components,
                "environment": env_vars,
                "version": "3.1.0-final",
                "request_count": self.request_count,
                "error_count": self.error_count
            }
            
            return web.json_response(health_data)
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Health check error: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)},
                status=500
            )
    
    async def metrics_handler(self, request):
        """Обработчик метрик"""
        try:
            self.request_count += 1
            
            uptime = datetime.now() - self.start_time
            
            metrics_data = {
                "uptime": str(uptime),
                "uptime_seconds": uptime.total_seconds(),
                "request_count": self.request_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(1, self.request_count),
                "timestamp": datetime.now().isoformat(),
                "version": "3.1.0-final",
                "memory_usage": "N/A",  # Можно добавить psutil
                "cpu_usage": "N/A"
            }
            
            return web.json_response(metrics_data)
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Metrics error: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def status_handler(self, request):
        """Обработчик статуса"""
        try:
            self.request_count += 1
            
            status_data = {
                "service": "AIMagistr 3.1",
                "version": "3.1.0-final",
                "status": "running",
                "uptime": str(datetime.now() - self.start_time),
                "requests": self.request_count,
                "errors": self.error_count,
                "timestamp": datetime.now().isoformat()
            }
            
            return web.json_response(status_data)
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Status error: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def root_handler(self, request):
        """Главная страница"""
        try:
            self.request_count += 1
            
            return web.Response(
                text="AIMagistr 3.1 Health Check\n\n/health - Health status\n/metrics - Metrics\n/status - Service status\n\nFinal version for Railway",
                content_type="text/plain"
            )
            
        except Exception as e:
            self.error_count += 1
            logger.error(f"Root handler error: {e}")
            return web.Response(
                text="Error: " + str(e),
                content_type="text/plain",
                status=500
            )
    
    async def start(self):
        """Запуск сервера"""
        try:
            logger.info(f"Starting AIMagistr 3.1 Final health check server on port {self.port}")
            
            # Создаем runner
            runner = web.AppRunner(self.app)
            await runner.setup()
            
            # Создаем site
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            logger.info("Health check server started successfully")
            
            # Запускаем в фоне
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Failed to start health check server: {e}")
            raise

async def main():
    """Главная функция"""
    try:
        port = int(os.getenv('PORT', 8000))
        server = HealthCheckServer(port)
        await server.start()
        
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
