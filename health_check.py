# -*- coding: utf-8 -*-
"""
Health Check сервер для AIMagistr 3.0
"""

import os
import asyncio
import logging
from aiohttp import web
from datetime import datetime
import json

# Импорты компонентов
try:
    from brain.ai_client import BrainManager
    from integrations.yandex_vision import YandexVision
    from integrations.yandex_translate import YandexTranslate
    from integrations.yandex_ocr import YandexOCR
    from data.rag_index import RAGIndex
    from security.secrets_scanner import SecretsScanner
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Некоторые компоненты недоступны: {e}")
    COMPONENTS_AVAILABLE = False


class HealthCheckServer:
    """Health Check сервер для мониторинга"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.logger = logging.getLogger("HealthCheck")
        
        # Инициализация компонентов
        self.components = {}
        self._init_components()
    
    def _init_components(self):
        """Инициализация компонентов для проверки"""
        try:
            if COMPONENTS_AVAILABLE:
                self.components = {
                    'brain': BrainManager(),
                    'vision': YandexVision(),
                    'translate': YandexTranslate(),
                    'ocr': YandexOCR(),
                    'rag': RAGIndex(),
                    'scanner': SecretsScanner()
                }
        except Exception as e:
            self.logger.error(f"Ошибка инициализации компонентов: {e}")
    
    async def health_check(self, request):
        """Основной health check endpoint"""
        try:
            start_time = datetime.now()
            
            # Проверяем компоненты
            component_status = {}
            overall_status = "healthy"
            
            for name, component in self.components.items():
                try:
                    if hasattr(component, 'health_check'):
                        status = await component.health_check()
                    elif hasattr(component, 'get_usage_stats'):
                        status = component.get_usage_stats()
                    else:
                        status = {"status": "unknown", "message": "No health check method"}
                    
                    component_status[name] = status
                    
                    if status.get('status') == 'error':
                        overall_status = "degraded"
                        
                except Exception as e:
                    component_status[name] = {
                        "status": "error",
                        "message": str(e)
                    }
                    overall_status = "degraded"
            
            # Проверяем переменные окружения
            env_status = self._check_environment()
            
            # Общая информация
            response_data = {
                "status": overall_status,
                "timestamp": datetime.now().isoformat(),
                "uptime": (datetime.now() - start_time).total_seconds(),
                "version": "3.0.0",
                "components": component_status,
                "environment": env_status,
                "system": {
                    "python_version": os.sys.version,
                    "platform": os.name,
                    "working_directory": os.getcwd()
                }
            }
            
            # Определяем HTTP статус
            http_status = 200 if overall_status == "healthy" else 503
            
            return web.json_response(response_data, status=http_status)
            
        except Exception as e:
            self.logger.error(f"Ошибка health check: {e}")
            return web.json_response({
                "status": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }, status=500)
    
    def _check_environment(self):
        """Проверка переменных окружения"""
        required_vars = [
            'YANDEX_API_KEY',
            'YANDEX_FOLDER_ID',
            'TELEGRAM_BOT_TOKEN'
        ]
        
        optional_vars = [
            'YANDEX_MODEL_URI',
            'SYSTEM_PROMPT',
            'MAX_FILE_SIZE_MB',
            'MAX_CONTEXT_TOKENS'
        ]
        
        env_status = {
            "required": {},
            "optional": {},
            "missing_required": [],
            "missing_optional": []
        }
        
        # Проверяем обязательные переменные
        for var in required_vars:
            value = os.getenv(var)
            if value:
                env_status["required"][var] = "✅ Set"
            else:
                env_status["required"][var] = "❌ Missing"
                env_status["missing_required"].append(var)
        
        # Проверяем опциональные переменные
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                env_status["optional"][var] = "✅ Set"
            else:
                env_status["optional"][var] = "⚠️ Not set"
                env_status["missing_optional"].append(var)
        
        return env_status
    
    async def metrics(self, request):
        """Метрики системы"""
        try:
            metrics_data = {
                "timestamp": datetime.now().isoformat(),
                "components": {}
            }
            
            # Собираем метрики от компонентов
            for name, component in self.components.items():
                try:
                    if hasattr(component, 'get_metrics'):
                        metrics_data["components"][name] = component.get_metrics()
                    elif hasattr(component, 'get_usage_stats'):
                        metrics_data["components"][name] = component.get_usage_stats()
                    elif hasattr(component, 'get_stats'):
                        metrics_data["components"][name] = component.get_stats()
                    else:
                        metrics_data["components"][name] = {"status": "no_metrics"}
                except Exception as e:
                    metrics_data["components"][name] = {"error": str(e)}
            
            return web.json_response(metrics_data)
            
        except Exception as e:
            self.logger.error(f"Ошибка получения метрик: {e}")
            return web.json_response({"error": str(e)}, status=500)
    
    async def status(self, request):
        """Простой статус endpoint"""
        return web.json_response({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "message": "AIMagistr 3.0 is running"
        })
    
    def create_app(self):
        """Создание приложения"""
        app = web.Application()
        
        # Регистрируем маршруты
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/metrics', self.metrics)
        app.router.add_get('/status', self.status)
        app.router.add_get('/', self.status)
        
        return app
    
    async def run(self):
        """Запуск сервера"""
        try:
            app = self.create_app()
            
            self.logger.info(f"Запуск Health Check сервера на порту {self.port}")
            
            runner = web.AppRunner(app)
            await runner.setup()
            
            site = web.TCPSite(runner, '0.0.0.0', self.port)
            await site.start()
            
            self.logger.info("Health Check сервер запущен")
            
            # Ждем бесконечно
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Ошибка запуска Health Check сервера: {e}")
            raise


async def main():
    """Главная функция"""
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Запуск сервера
    server = HealthCheckServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
