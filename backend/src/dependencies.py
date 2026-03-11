"""Dependency injection for FastAPI application."""

from typing import AsyncGenerator

import httpx
from fastapi import FastAPI

from src.services.cache import TTLCache


def get_cache(app: FastAPI) -> TTLCache:
    """Get cache singleton from app state."""
    cache: TTLCache = app.state.cache
    return cache


def get_http_client(app: FastAPI) -> httpx.AsyncClient:
    """Get HTTP client singleton from app state."""
    client: httpx.AsyncClient = app.state.http_client
    return client


async def cache_dependency(app: FastAPI) -> AsyncGenerator[TTLCache, None]:
    """Dependency for injecting cache into route handlers."""
    yield get_cache(app)


async def http_client_dependency(app: FastAPI) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Dependency for injecting HTTP client into route handlers."""
    yield get_http_client(app)
