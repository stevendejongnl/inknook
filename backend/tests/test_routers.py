"""Tests for API routers."""

import pytest

from src.services.cache import TTLCache


def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_cache_status_endpoint_empty(client, app):
    """Test cache status endpoint with empty cache."""
    response = client.get("/cache/status")
    assert response.status_code == 200
    assert response.json() == {}


@pytest.mark.asyncio
async def test_cache_status_endpoint_with_data(client, app):
    """Test cache status endpoint with cached data."""
    cache: TTLCache = app.state.cache
    await cache.set("ha", {"temperature": 22.5}, ttl_seconds=300)

    response = client.get("/cache/status")
    assert response.status_code == 200

    status = response.json()
    assert "ha" in status
    assert not status["ha"]["expired"]


def test_display_bmp_endpoint(client, app):
    """Test BMP display endpoint returns image."""
    response = client.get("/display.bmp")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/bmp"
    assert len(response.content) > 0

    # Verify BMP magic bytes
    assert response.content[:2] == b"BM"


def test_display_png_endpoint(client, app):
    """Test PNG display endpoint returns image."""
    response = client.get("/display.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert len(response.content) > 0

    # Verify PNG magic bytes
    assert response.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_display_bmp_with_force_refresh(client, app):
    """Test BMP endpoint with force_refresh parameter."""
    # First request
    response1 = client.get("/display.bmp")
    assert response1.status_code == 200

    # Second request with force_refresh
    response2 = client.get("/display.bmp?force_refresh=true")
    assert response2.status_code == 200

    # Both should be valid images (might be slightly different due to timestamps)
    assert len(response2.content) > 0


def test_display_endpoint_without_valid_credentials(client, app):
    """Test display endpoint gracefully handles missing credentials."""
    # With invalid/missing credentials, endpoint should still return an image
    response = client.get("/display.bmp")
    assert response.status_code == 200
    assert len(response.content) > 0
    assert response.content[:2] == b"BM"  # Valid BMP


@pytest.mark.asyncio
async def test_cache_status_persists_across_requests(client, app):
    """Test that cache data persists across multiple requests."""
    cache: TTLCache = app.state.cache
    test_data = {"temperature": 25.0}
    await cache.set("test", test_data, ttl_seconds=600)

    # Make a request
    response1 = client.get("/cache/status")
    assert "test" in response1.json()

    # Make another request - should still have cached data
    response2 = client.get("/cache/status")
    assert "test" in response2.json()
    assert response1.json()["test"]["expires_at"] == response2.json()["test"]["expires_at"]
