"""FastAPI application factory with lifespan management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from src.config import settings
from src.routers import cache, display, health
from src.services.cache import TTLCache

logger = logging.getLogger(__name__)
logging.basicConfig(level=settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: startup and shutdown."""
    # STARTUP
    cache = TTLCache()
    app.state.cache = cache

    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    app.state.http_client = http_client

    logger.info("epaper-backend started; cache initialized")

    try:
        yield
    finally:
        # SHUTDOWN
        await http_client.aclose()
        logger.info("HTTP client closed")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="epaper-backend",
        description="Renders 800x480 B/W e-paper dashboard from Home Assistant, InfluxDB, Google Calendar",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(health.router)
    app.include_router(display.router)
    app.include_router(cache.router)

    return app


app = create_app()
