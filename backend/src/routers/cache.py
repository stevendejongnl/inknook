"""Cache status endpoint for debugging."""

from fastapi import APIRouter, Request

from src.services.cache import TTLCache

router = APIRouter(tags=["debug"])


@router.get("/cache/status")
async def cache_status(request: Request) -> dict:
    """Get current cache status for all sources."""
    app = request.app
    cache: TTLCache = app.state.cache
    return cache.status()
