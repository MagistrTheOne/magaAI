"""FastAPI application with Telegram webhook endpoints."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from app.settings import settings
from app.schemas import HealthResponse
from app.router import dp, bot, set_webhook, close_bot
from app.middleware.webhook_guard import validate_webhook_request
from app.observability.metrics import get_metrics_response, get_metrics_summary
from app.observability.logging import setup_logging, app_logger

# Setup structured logging
setup_logging(settings.log_level)
logger = app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting AI-Maga Telegram Assistant...")
    await set_webhook()

    yield

    # Shutdown
    logger.info("Shutting down AI-Maga...")
    await close_bot()


# Create FastAPI app
app = FastAPI(
    title="AI-Maga Telegram Assistant",
    description="AI-powered Telegram assistant with voice/text responses",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics_response()


@app.get("/readyz")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # Check external dependencies
        # For now, just return OK - in production, check Yandex API connectivity
        return {"status": "ready", "dependencies": {"yandex_api": "ok"}}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service not ready")


@app.get("/services")
async def services_status():
    """Services status endpoint."""
    return {
        "services": {
            "telegram_bot": "running",
            "yandex_llm": "available",
            "yandex_tts": "available",
            "yandex_stt": "available" if settings.yandex_stt_enable else "disabled"
        },
        "metrics": get_metrics_summary()
    }


@app.get("/version")
async def version():
    """Version endpoint."""
    return {
        "version": "1.0.0",
        "build": os.getenv("BUILD_ID", "unknown"),
        "environment": os.getenv("ENVIRONMENT", "development")
    }


@app.post("/webhook/telegram/{secret}")
async def telegram_webhook(secret: str, request: Request):
    """
    Telegram webhook endpoint.

    Args:
        secret: Webhook secret for validation
        request: Raw request with update data
    """
    try:
        # Validate webhook request
        validate_webhook_request(secret, request)

        # Get update data
        update_data = await request.json()

        # Process update with aiogram
        await dp.feed_webhook_update(bot, update_data)

        return {"ok": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def main():
    """Main entry point for running the application."""
    import uvicorn

    host = "0.0.0.0"
    port = int(os.getenv("PORT", settings.port))

    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"Webhook URL: {settings.webhook_url}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,  # Disable reload for production
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()