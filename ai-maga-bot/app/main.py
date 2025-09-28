"""
Главный файл FastAPI приложения с webhook для Telegram бота.
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

from app.settings import settings
from app.router import dp, bot, set_webhook, close_bot
from app.middleware.webhook_guard import validate_webhook_request, validate_zoom_webhook_request
from app.schemas import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info("Запуск приложения...")
    try:
        # Инициализируем оркестратор
        from app.orchestrator import get_orchestrator
        orchestrator = await get_orchestrator()
        logger.info("Оркестратор инициализирован")

        await set_webhook()
        logger.info("Приложение запущено успешно")
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        raise

    yield

    # Shutdown
    logger.info("Завершение работы приложения...")
    try:
        await close_bot()
        logger.info("Приложение завершено")
    except Exception as e:
        logger.error(f"Ошибка при завершении приложения: {e}")


# Создаем FastAPI приложение
app = FastAPI(
    title="AI-Maga Telegram Bot",
    description="Telegram бот с интеграцией Yandex LLM и SpeechKit",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.post(f"/webhook/telegram/{{secret}}")
async def telegram_webhook(secret: str, request: Request):
    """
    Webhook endpoint для Telegram.
    
    Args:
        secret: Секрет из URL
        request: HTTP запрос
        
    Returns:
        JSONResponse: Ответ Telegram
    """
    try:
        # Валидируем запрос
        validate_webhook_request(secret, request)
        
        # Получаем данные обновления
        update_data = await request.json()
        
        logger.debug(f"Получено обновление: {update_data.get('update_id', 'unknown')}")
        
        # Передаем обновление в aiogram
        await dp.feed_webhook_update(bot, update_data)
        
        return JSONResponse(content={"ok": True})
        
    except HTTPException as e:
        logger.warning(f"HTTP ошибка в webhook: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.detail}
        )
    except Exception as e:
        logger.error(f"Неожиданная ошибка в webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )


@app.post("/webhook/zoom")
async def zoom_webhook(request: Request):
    """
    Webhook endpoint для Zoom.
    
    Args:
        request: HTTP запрос от Zoom
        
    Returns:
        JSONResponse: Ответ Zoom
    """
    try:
        # Валидируем запрос
        validate_zoom_webhook_request(request)
        
        # Получаем данные события
        event_data = await request.json()
        
        logger.info(f"Получен Zoom webhook: {event_data.get('event', 'unknown')}")
        
        # Получаем оркестратор и обрабатываем событие
        from app.orchestrator import get_orchestrator
        orchestrator = await get_orchestrator()
        
        result = await orchestrator.on_zoom_webhook(event_data)
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        logger.warning(f"HTTP ошибка в Zoom webhook: {e.detail}")
        return JSONResponse(
            status_code=e.status_code,
            content={"error": e.detail}
        )
    except Exception as e:
        logger.error(f"Ошибка обработки Zoom webhook: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "message": "AI-Maga Telegram Bot API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/dashboard")
async def dashboard():
    """Веб-интерфейс управления."""
    from app.orchestrator import orchestrator

    services_status = {}
    if orchestrator.initialized:
        for service_name in orchestrator.get_available_services():
            services_status[service_name] = orchestrator.get_service_status(service_name)

    return {
        "title": "AI-Maga Control Panel",
        "services": services_status,
        "active_tasks": len(orchestrator.active_tasks) if orchestrator.initialized else 0,
        "total_components": len(orchestrator.components) if orchestrator.initialized else 0
    }


@app.get("/health")
async def health_check_detailed():
    """Подробная проверка здоровья системы."""
    from app.orchestrator import orchestrator

    if not orchestrator.initialized:
        return {
            "status": "initializing",
            "message": "Оркестратор еще инициализируется"
        }

    try:
        health_status = await orchestrator.get_health_status()
        return health_status
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка получения статуса здоровья: {str(e)}"
        }


@app.get("/metrics")
async def system_metrics():
    """Системные метрики."""
    from app.orchestrator import orchestrator

    if not orchestrator.initialized:
        return {
            "status": "initializing",
            "message": "Оркестратор еще инициализируется"
        }

    try:
        metrics = orchestrator.get_system_metrics()
        return metrics
    except Exception as e:
        return {
            "status": "error",
            "message": f"Ошибка получения метрик: {str(e)}"
        }


@app.get("/services")
async def list_services():
    """Получить список доступных сервисов."""
    from app.orchestrator import orchestrator

    if not orchestrator.initialized:
        return {"error": "Оркестратор не инициализирован"}

    return {
        "services": orchestrator.get_available_services(),
        "details": {
            name: orchestrator.get_service_status(name)
            for name in orchestrator.get_available_services()
        }
    }


@app.post("/command")
async def execute_command(command: str, user_id: int = 0):
    """Выполнить команду через оркестратор."""
    from app.orchestrator import orchestrator

    if not orchestrator.initialized:
        return {"error": "Оркестратор не инициализирован"}

    try:
        result = await orchestrator.process_message(user_id, command, "text")
        return result
    except Exception as e:
        return {"error": str(e)}


def main():
    """Главная функция запуска приложения."""
    logger.info(f"Запуск сервера на порту {settings.port}")
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level=settings.log_level.lower(),
        access_log=True
    )


if __name__ == "__main__":
    main()
