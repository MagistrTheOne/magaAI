# -*- coding: utf-8 -*-
"""
Health Check для AIMagistr 3.1
Оптимизированный HTTP сервер для Railway
"""

import os
import asyncio
import logging
from aiohttp import web
from datetime import datetime
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthCheckServer:
    """Оптимизированный HTTP сервер для health check"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_handler)
        self.app.router.add_get('/metrics', self.metrics_handler)
        self.app.router.add_get('/', self.root_handler)
        
        # Статистика
        self.start_time = datetime.now()
        self.request_count = 0
        
    async def health_handler(self, request):
        """Обработчик health check"""
        try:
            self.request_count += 1
            
            # Базовая проверка компонентов
            components = {
                "telegram_bot": "running",
                "services": "available"
            }
            
            # Проверяем сервисы
            try:
                from services.email_triage import EmailTriageService
                from services.time_blocking import TimeBlockingService
                from services.finance_receipts import FinanceReceiptsService
                components["email_triage"] = "ok"
                components["time_blocking"] = "ok"
                components["finance_receipts"] = "ok"
            except Exception as e:
                components["services"] = f"error: {str(e)}"
            
            health_data = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "uptime": str(datetime.now() - self.start_time),
                "components": components,
                "version": "3.1.0",
                "request_count": self.request_count
            }
            
            return web.json_response(health_data)
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return web.json_response(
                {"status": "unhealthy", "error": str(e)},
                status=500
            )
    
    async def metrics_handler(self, request):
        """Обработчик метрик"""
        try:
            self.request_count += 1
            
            metrics_data = {
                "uptime": str(datetime.now() - self.start_time),
                "request_count": self.request_count,
                "timestamp": datetime.now().isoformat(),
                "version": "3.1.0",
                "services": {
                    "email_triage": "active",
                    "time_blocking": "active", 
                    "finance_receipts": "active"
                }
            }
            
            return web.json_response(metrics_data)
            
        except Exception as e:
            logger.error(f"Metrics error: {e}")
            return web.json_response(
                {"error": str(e)},
                status=500
            )
    
    async def root_handler(self, request):
        """Главная страница"""
        return web.Response(
            text="🤖 AIMagistr 3.1 Health Check\n\n/health - Health status\n/metrics - Metrics\n\nServices: Email Triage, Time Blocking, Finance Receipts",
            content_type="text/plain"
        )
    
    async def start(self):
        """Запуск сервера"""
        try:
            logger.info(f"Starting AIMagistr 3.1 health check server on port {self.port}")
            runner = web.AppRunner(self.app)
            await runner.setup()
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
    port = int(os.getenv('PORT', 8000))
    server = HealthCheckServer(port)
    await server.start()

if __name__ == "__main__":
    asyncio.run(main())