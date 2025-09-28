"""FastAPI application with Telegram webhook endpoints."""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.settings import settings
from app.schemas import HealthResponse
from app.router import dp, bot, set_webhook, close_bot
from app.middleware.webhook_guard import validate_webhook_request

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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