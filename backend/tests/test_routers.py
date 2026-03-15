"""Tests for API routers."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.config import DepartureConfig, SensorConfig
from src.routers.display import _build_departures_display, _build_sensors_display
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


# ── _build_sensors_display ─────────────────────────────────────────────────────

def test_build_sensors_happy_path():
    cfgs = [SensorConfig(entity_id="sensor.temp", label="Temp")]
    entities = [{"state": "21.5", "attributes": {"unit_of_measurement": "°C"}}]
    result = _build_sensors_display(cfgs, entities)
    assert result == [{"label": "Temp", "value": "21.5", "unit": "°C"}]


def test_build_sensors_error_skipped():
    cfgs = [SensorConfig(entity_id="sensor.temp", label="Temp")]
    entities = [{"error": "timeout"}]
    assert _build_sensors_display(cfgs, entities) == []


def test_build_sensors_unavailable():
    cfgs = [SensorConfig(entity_id="sensor.temp", label="Temp")]
    entities = [{"state": "unavailable", "attributes": {}}]
    result = _build_sensors_display(cfgs, entities)
    assert result[0]["value"] == "N/A"
    assert result[0]["unit"] == ""


def test_build_sensors_binary_known_device_class():
    cfgs = [SensorConfig(entity_id="binary_sensor.door", label="Door")]
    entities = [{"state": "on", "attributes": {"device_class": "door"}}]
    result = _build_sensors_display(cfgs, entities)
    assert result[0]["value"] == "Open"


def test_build_sensors_binary_off_known_device_class():
    cfgs = [SensorConfig(entity_id="binary_sensor.door", label="Door")]
    entities = [{"state": "off", "attributes": {"device_class": "door"}}]
    result = _build_sensors_display(cfgs, entities)
    assert result[0]["value"] == "Closed"


def test_build_sensors_binary_unknown_device_class():
    cfgs = [SensorConfig(entity_id="binary_sensor.x", label="X")]
    entities = [{"state": "off", "attributes": {"device_class": "unknown"}}]
    result = _build_sensors_display(cfgs, entities)
    assert result[0]["value"] == "Off"


def test_build_sensors_binary_on_unknown_device_class():
    cfgs = [SensorConfig(entity_id="binary_sensor.x", label="X")]
    entities = [{"state": "on", "attributes": {"device_class": "unknown"}}]
    result = _build_sensors_display(cfgs, entities)
    assert result[0]["value"] == "On"


def test_build_sensors_custom_unit_override():
    cfgs = [SensorConfig(entity_id="sensor.temp", label="Temp", unit="F")]
    entities = [{"state": "72", "attributes": {"unit_of_measurement": "°C"}}]
    result = _build_sensors_display(cfgs, entities)
    assert result[0]["unit"] == "F"  # cfg.unit overrides HA unit


def test_build_sensors_all_device_classes():
    # These all map to specific labels (not the generic On/Off fallback)
    non_on_off = {
        "door": ("Open", "Closed"),
        "window": ("Open", "Closed"),
        "motion": ("Motion", "Clear"),
        "lock": ("Unlocked", "Locked"),
        "presence": ("Home", "Away"),
        "occupancy": ("Occupied", "Clear"),
        "smoke": ("Alarm", "Clear"),
    }
    for dc, (on_lbl, _) in non_on_off.items():
        cfgs = [SensorConfig(entity_id=f"binary_sensor.{dc}", label=dc.capitalize())]
        entities = [{"state": "on", "attributes": {"device_class": dc}}]
        result = _build_sensors_display(cfgs, entities)
        assert len(result) == 1
        assert result[0]["value"] == on_lbl


def test_build_sensors_empty_entity():
    """Empty entity dict is falsy → treated as missing, skipped."""
    cfgs = [SensorConfig(entity_id="sensor.temp", label="Temp")]
    entities = [{}]
    result = _build_sensors_display(cfgs, entities)
    assert result == []


# ── _build_departures_display ──────────────────────────────────────────────────

def test_build_departures_happy_path():
    tz = ZoneInfo("UTC")
    future = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
    cfgs = [DepartureConfig(entity_id="sensor.bus", short_direction="CS")]
    entities = [{"attributes": {
        "line_name": "340",
        "direction": "Haarlem",
        "times": [{"planned": future}]
    }}]
    result = _build_departures_display(cfgs, entities, tz)
    assert len(result) == 1
    assert result[0]["line"] == "340"
    assert result[0]["direction"] == "CS"  # short_direction override
    assert len(result[0]["times"]) == 1


def test_build_departures_uses_entity_direction_when_no_short():
    tz = ZoneInfo("UTC")
    future = (datetime.now(UTC) + timedelta(minutes=10)).isoformat()
    cfgs = [DepartureConfig(entity_id="sensor.bus")]
    entities = [{"attributes": {
        "line_name": "340",
        "direction": "Haarlem Station",
        "times": [{"planned": future}]
    }}]
    result = _build_departures_display(cfgs, entities, tz)
    assert result[0]["direction"] == "Haarlem Station"


def test_build_departures_past_skipped():
    tz = ZoneInfo("UTC")
    past = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    cfgs = [DepartureConfig(entity_id="sensor.bus")]
    entities = [{"attributes": {
        "line_name": "1", "direction": "A",
        "times": [{"planned": past}]
    }}]
    result = _build_departures_display(cfgs, entities, tz)
    assert result[0]["times"] == []


def test_build_departures_invalid_iso_skipped():
    tz = ZoneInfo("UTC")
    cfgs = [DepartureConfig(entity_id="sensor.bus")]
    entities = [{"attributes": {
        "line_name": "1", "direction": "A",
        "times": [{"planned": "not-a-date"}]
    }}]
    result = _build_departures_display(cfgs, entities, tz)
    assert result[0]["times"] == []


def test_build_departures_error_entity_skipped():
    tz = ZoneInfo("UTC")
    cfgs = [DepartureConfig(entity_id="sensor.bus")]
    entities = [{"error": "timeout"}]
    assert _build_departures_display(cfgs, entities, tz) == []


def test_build_departures_delay_calculation():
    tz = ZoneInfo("UTC")
    planned = datetime.now(UTC) + timedelta(minutes=10)
    estimated = planned + timedelta(minutes=3)
    cfgs = [DepartureConfig(entity_id="sensor.bus")]
    entities = [{"attributes": {
        "line_name": "1", "direction": "A",
        "times": [{"planned": planned.isoformat(), "estimated": estimated.isoformat()}]
    }}]
    result = _build_departures_display(cfgs, entities, tz)
    assert result[0]["times"][0]["delay_min"] == 3


def test_build_departures_max_departures_respected():
    tz = ZoneInfo("UTC")
    times = [
        {"planned": (datetime.now(UTC) + timedelta(minutes=i + 5)).isoformat()}
        for i in range(10)
    ]
    cfgs = [DepartureConfig(entity_id="sensor.bus", max_departures=3)]
    entities = [{"attributes": {"line_name": "1", "direction": "A", "times": times}}]
    result = _build_departures_display(cfgs, entities, tz)
    assert len(result[0]["times"]) == 3
