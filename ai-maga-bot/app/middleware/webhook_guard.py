"""
Middleware для защиты webhook и rate limiting.
"""
import logging
import time
from typing import Dict, Optional
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from app.settings import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Простой rate limiter для защиты от флуда."""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Инициализация rate limiter.
        
        Args:
            max_requests: Максимальное количество запросов
            window_seconds: Окно времени в секундах
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
    
    def is_allowed(self, client_ip: str) -> bool:
        """
        Проверить, разрешен ли запрос.
        
        Args:
            client_ip: IP адрес клиента
            
        Returns:
            bool: True если запрос разрешен
        """
        now = time.time()
        
        # Очищаем старые запросы
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if now - req_time < self.window_seconds
            ]
        else:
            self.requests[client_ip] = []
        
        # Проверяем лимит
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit превышен для IP {client_ip}")
            return False
        
        # Добавляем текущий запрос
        self.requests[client_ip].append(now)
        return True


# Глобальный экземпляр rate limiter
rate_limiter = RateLimiter(max_requests=20, window_seconds=60)


def validate_webhook_secret(secret: str) -> bool:
    """
    Валидировать секрет webhook.
    
    Args:
        secret: Секрет из URL
        
    Returns:
        bool: True если секрет валиден
    """
    return secret == settings.telegram_webhook_secret


def validate_telegram_token(request: Request) -> bool:
    """
    Валидировать токен Telegram (опционально).
    
    Args:
        request: HTTP запрос
        
    Returns:
        bool: True если токен валиден
    """
    # Проверяем заголовок X-Telegram-Bot-Api-Secret-Token
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_token:
        return secret_token == settings.telegram_webhook_secret
    
    # Если заголовок не установлен, считаем валидным (для совместимости)
    return True


def get_client_ip(request: Request) -> str:
    """
    Получить IP адрес клиента.
    
    Args:
        request: HTTP запрос
        
    Returns:
        str: IP адрес
    """
    # Проверяем заголовки прокси
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Возвращаем IP напрямую
    return request.client.host if request.client else "unknown"


async def webhook_guard_middleware(request: Request, call_next):
    """
    Middleware для защиты webhook.
    
    Args:
        request: HTTP запрос
        call_next: Следующий обработчик
        
    Returns:
        Response: HTTP ответ
    """
    try:
        # Получаем IP клиента
        client_ip = get_client_ip(request)
        
        # Проверяем rate limit
        if not rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit превышен для IP {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"error": "Too Many Requests", "retry_after": 60}
            )
        
        # Проверяем токен Telegram (если установлен)
        if not validate_telegram_token(request):
            logger.warning(f"Неверный токен Telegram от IP {client_ip}")
            return JSONResponse(
                status_code=403,
                content={"error": "Forbidden"}
            )
        
        # Продолжаем обработку
        response = await call_next(request)
        return response
        
    except Exception as e:
        logger.error(f"Ошибка в webhook guard middleware: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )


def validate_webhook_request(secret: str, request: Request) -> None:
    """
    Валидировать запрос webhook.
    
    Args:
        secret: Секрет из URL
        request: HTTP запрос
        
    Raises:
        HTTPException: При невалидном запросе
    """
    # Проверяем секрет
    if not validate_webhook_secret(secret):
        logger.warning(f"Неверный секрет webhook: {secret}")
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Проверяем токен Telegram
    if not validate_telegram_token(request):
        logger.warning("Неверный токен Telegram")
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Проверяем rate limit
    client_ip = get_client_ip(request)
    if not rate_limiter.is_allowed(client_ip):
        logger.warning(f"Rate limit превышен для IP {client_ip}")
        raise HTTPException(status_code=429, detail="Too Many Requests")
