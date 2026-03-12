"""Pytest configuration and shared fixtures."""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock environment variables before importing settings
os.environ.setdefault("HA_URL", "http://localhost:8123")
os.environ.setdefault("HA_TOKEN", "test-token")
os.environ.setdefault("INFLUXDB_URL", "http://localhost:8086")
os.environ.setdefault("INFLUXDB_TOKEN", "test-token")
os.environ.setdefault("INFLUXDB_BUCKET", "home")
os.environ.setdefault("INFLUXDB_ORG", "my-org")
os.environ.setdefault("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "")

from fastapi.testclient import TestClient

from src.main import create_app
from src.services.cache import TTLCache


@pytest.fixture
def app():
    """Create test FastAPI application."""
    test_app = create_app()
    # Override cache with test instance
    test_app.state.cache = TTLCache()
    # Mock http_client for testing (prevent actual API calls)
    mock_http_client = MagicMock()
    test_app.state.http_client = mock_http_client
    return test_app


@pytest.fixture
def client(app):
    """Create HTTP client for testing."""
    return TestClient(app)


def load_fixture(filename: str) -> dict:
    """Load JSON fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / filename
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def ha_sensor_response():
    """Sample Home Assistant /api/states/{entity_id} response."""
    return load_fixture("home_assistant/sensor_response.json")


@pytest.fixture
def influxdb_flux_response():
    """Sample InfluxDB Flux query response."""
    return load_fixture("influxdb/flux_response.json")


@pytest.fixture
def google_calendar_events():
    """Sample Google Calendar upcoming events response."""
    return load_fixture("google_calendar/events.json")
