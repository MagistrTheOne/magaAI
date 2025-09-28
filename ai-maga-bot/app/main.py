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
from app.middleware.webhook_guard import validate_webhook_request
from app.schemas import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info("Запуск приложения...")
    try:
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


@app.get("/")
async def root():
    """Корневой endpoint."""
    return {
        "message": "AI-Maga Telegram Bot API",
        "version": "1.0.0",
        "status": "running"
    }


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
