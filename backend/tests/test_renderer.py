"""Tests for dashboard renderer."""

from PIL import Image

import pytest

from src.services.renderer import render_dashboard


def test_render_dashboard_output_format():
    """Test that renderer produces correct BMP format and dimensions."""
    image_bytes = render_dashboard(None, None, None, format="BMP")

    assert image_bytes is not None
    assert len(image_bytes) > 0
    assert image_bytes[:2] == b"BM"  # BMP magic bytes


def test_render_dashboard_png_format():
    """Test PNG output format."""
    image_bytes = render_dashboard(None, None, None, format="PNG")

    assert image_bytes is not None
    assert len(image_bytes) > 0
    assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_render_dashboard_dimensions():
    """Test that image has correct dimensions."""
    image_bytes = render_dashboard(None, None, None, format="BMP")

    # Load image and verify dimensions
    from io import BytesIO

    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)
    assert img.mode == "1"  # 1-bit B/W


def test_render_dashboard_with_ha_data():
    """Test rendering with Home Assistant data."""
    ha_data = {
        "state": "cloudy",
        "attributes": {
            "temperature": 18.5,
            "humidity": 65,
            "pressure": 1013,
            "wind_speed": 12,
            "condition": "cloudy",
        },
    }

    image_bytes = render_dashboard(ha_data=ha_data, format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_with_influx_data():
    """Test rendering with InfluxDB data."""
    influx_data = {
        "temperature_avg": 22.5,
        "humidity_avg": 60.0,
        "pressure": 1013,
    }

    image_bytes = render_dashboard(influx_data=influx_data, format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_with_calendar_data():
    """Test rendering with calendar events."""
    calendar_data = [
        {
            "summary": "Standup",
            "start": "2026-03-10T09:30:00+01:00",
            "end": "2026-03-10T10:00:00+01:00",
        },
        {
            "summary": "Team meeting",
            "start": "2026-03-10T14:00:00+01:00",
            "end": "2026-03-10T15:00:00+01:00",
        },
    ]

    image_bytes = render_dashboard(calendar_data=calendar_data, format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_graceful_degradation_ha_error():
    """Test graceful handling of HA errors."""
    ha_data = {"error": "Failed to fetch"}

    image_bytes = render_dashboard(ha_data=ha_data, format="BMP")
    assert len(image_bytes) > 0

    # Verify image can be loaded
    from io import BytesIO

    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)


def test_render_dashboard_all_data_combined():
    """Test rendering with all data sources."""
    ha_data = {
        "state": "cloudy",
        "attributes": {
            "temperature": 18.5,
            "wind_speed": 12,
            "condition": "cloudy",
        },
    }
    influx_data = {
        "temperature_avg": 22.5,
        "humidity_avg": 60.0,
        "pressure": 1013,
    }
    calendar_data = [
        {
            "summary": "Standup",
            "start": "2026-03-10T09:30:00+01:00",
            "end": "2026-03-10T10:00:00+01:00",
        },
    ]

    image_bytes = render_dashboard(
        ha_data=ha_data,
        influx_data=influx_data,
        calendar_data=calendar_data,
        format="BMP",
    )

    assert len(image_bytes) > 0

    from io import BytesIO

    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)
    assert img.mode == "1"
