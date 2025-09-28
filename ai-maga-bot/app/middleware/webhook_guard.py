"""Webhook guard middleware for secret validation and rate limiting."""

import time
from typing import Dict
from fastapi import Request, HTTPException
from app.settings import settings


class RateLimiter:
    """Simple rate limiter for webhook protection."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}  # client_ip -> timestamps

    def is_allowed(self, client_ip: str) -> bool:
        """
        Check if request is allowed.

        Args:
            client_ip: Client IP address

        Returns:
            True if allowed, False if rate limited
        """
        now = time.time()

        if client_ip not in self.requests:
            self.requests[client_ip] = []

        # Clean old requests
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip]
            if now - ts < self.window_seconds
        ]

        # Check if under limit
        if len(self.requests[client_ip]) < self.max_requests:
            self.requests[client_ip].append(now)
            return True

        return False


# Global rate limiter instance
rate_limiter = RateLimiter()


def validate_webhook_secret(secret: str) -> bool:
    """
    Validate webhook secret.

    Args:
        secret: Secret from URL path

    Returns:
        True if valid
    """
    return secret == settings.telegram_webhook_secret


async def validate_telegram_token(request: Request) -> bool:
    """
    Validate that this is a legitimate Telegram request.
    Basic validation - in production, implement full webhook validation.

    Args:
        request: FastAPI request

    Returns:
        True if valid Telegram request
    """
    # Basic check for Telegram user agent or headers
    user_agent = request.headers.get("user-agent", "").lower()
    return "telegram" in user_agent or "bot" in user_agent


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Args:
        request: FastAPI request

    Returns:
        Client IP address
    """
    # Check for forwarded headers (common in proxies/load balancers)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fallback to direct client
    return request.client.host if request.client else "unknown"


async def webhook_guard_middleware(request: Request, call_next):
    """
    Webhook guard middleware for security.

    Args:
        request: FastAPI request
        call_next: Next middleware/route handler

    Returns:
        Response from next handler
    """
    # Get client IP for rate limiting
    client_ip = get_client_ip(request)

    # Apply rate limiting
    if not rate_limiter.is_allowed(client_ip):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded"
        )

    # Continue with request
    response = await call_next(request)
    return response


def validate_webhook_request(secret: str, request: Request) -> None:
    """
    Validate webhook request completely.

    Args:
        secret: Secret from URL
        request: FastAPI request

    Raises:
        HTTPException: If validation fails
    """
    # Validate secret
    if not validate_webhook_secret(secret):
        raise HTTPException(
            status_code=403,
            detail="Invalid webhook secret"
        )

    # Validate Telegram request (basic)
    # Note: In production, implement full webhook validation with bot token
    # if not await validate_telegram_token(request):
    #     raise HTTPException(
    #         status_code=403,
    #         detail="Invalid Telegram request"
    #     )


def validate_zoom_webhook_request(request: Request) -> None:
    """
    Placeholder for Zoom webhook validation.
    Not implemented yet.

    Args:
        request: FastAPI request
    """
    pass  # Zoom webhook validation would go here