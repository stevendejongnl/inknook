"""Tests for FastAPI dependency injection helpers."""

import httpx
import pytest
from fastapi import FastAPI

from src.dependencies import (
    cache_dependency,
    get_cache,
    get_http_client,
    http_client_dependency,
)
from src.services.cache import TTLCache


@pytest.fixture
def dep_app():
    """Minimal FastAPI app with cache and http_client on state."""
    app = FastAPI()
    app.state.cache = TTLCache()
    app.state.http_client = httpx.AsyncClient()
    return app


def test_get_cache(dep_app):
    result = get_cache(dep_app)
    assert result is dep_app.state.cache
    assert isinstance(result, TTLCache)


def test_get_http_client(dep_app):
    result = get_http_client(dep_app)
    assert result is dep_app.state.http_client
    assert isinstance(result, httpx.AsyncClient)


@pytest.mark.asyncio
async def test_cache_dependency(dep_app):
    collected = []
    async for cache in cache_dependency(dep_app):
        collected.append(cache)
    assert len(collected) == 1
    assert collected[0] is dep_app.state.cache


@pytest.mark.asyncio
async def test_http_client_dependency(dep_app):
    collected = []
    async for client in http_client_dependency(dep_app):
        collected.append(client)
    assert len(collected) == 1
    assert collected[0] is dep_app.state.http_client
