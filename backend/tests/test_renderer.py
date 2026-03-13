"""Tests for dashboard renderer."""

from io import BytesIO

from PIL import Image

from src.services.renderer import render_dashboard, _draw_precip_chart
from PIL import ImageDraw


def test_render_dashboard_output_format():
    """Test that renderer produces correct BMP format and dimensions."""
    image_bytes = render_dashboard(None, None, None, output_format="BMP")

    assert image_bytes is not None
    assert len(image_bytes) > 0
    assert image_bytes[:2] == b"BM"  # BMP magic bytes


def test_render_dashboard_png_format():
    """Test PNG output format."""
    image_bytes = render_dashboard(None, None, None, output_format="PNG")

    assert image_bytes is not None
    assert len(image_bytes) > 0
    assert image_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic bytes


def test_render_dashboard_dimensions():
    """Test that image has correct dimensions."""
    image_bytes = render_dashboard(None, None, None, output_format="BMP")

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

    image_bytes = render_dashboard(ha_data=ha_data, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_with_influx_data():
    """Test rendering with InfluxDB data."""
    influx_data = {
        "temperature_avg": 22.5,
        "humidity_avg": 60.0,
        "pressure": 1013,
    }

    image_bytes = render_dashboard(influx_data=influx_data, output_format="BMP")
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

    image_bytes = render_dashboard(calendar_data=calendar_data, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_graceful_degradation_ha_error():
    """Test graceful handling of HA errors."""
    ha_data = {"error": "Failed to fetch"}

    image_bytes = render_dashboard(ha_data=ha_data, output_format="BMP")
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
        output_format="BMP",
    )

    assert len(image_bytes) > 0

    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)
    assert img.mode == "1"


def test_render_dashboard_with_forecast_data():
    """Test rendering with 24h forecast entries (precipitation chart)."""
    ha_data = {
        "state": "rainy",
        "attributes": {"temperature": 14.0, "wind_speed": 8},
    }
    forecast_data = [
        {"datetime": f"2026-03-13T{h:02d}:00:00+01:00", "precipitation": h * 0.1}
        for h in range(24)
    ]
    image_bytes = render_dashboard(ha_data=ha_data, forecast_data=forecast_data, output_format="BMP")
    assert len(image_bytes) > 0
    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)


def test_render_dashboard_with_empty_forecast():
    """Test rendering with empty forecast list (no chart, no crash)."""
    ha_data = {"state": "sunny", "attributes": {"temperature": 22.0, "wind_speed": 5}}
    image_bytes = render_dashboard(ha_data=ha_data, forecast_data=[], output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_with_sensors_display():
    """Test rendering with configurable sensors list."""
    sensors_display = [
        {"label": "Living Room", "value": "21.3", "unit": "°C"},
        {"label": "Humidity", "value": "58", "unit": "%"},
        {"label": "Front Door", "value": "Closed", "unit": ""},
    ]
    image_bytes = render_dashboard(sensors_display=sensors_display, output_format="BMP")
    assert len(image_bytes) > 0
    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)


def test_render_dashboard_sensors_panel_empty():
    """Test sensors panel with empty list shows fallback text."""
    image_bytes = render_dashboard(sensors_display=[], output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_mdi_font_fallback():
    """Test that renderer doesn't crash when MDI font is unavailable."""
    import unittest.mock as mock
    with mock.patch("src.services.renderer._ensure_mdi_font", return_value=None):
        ha_data = {"state": "sunny", "attributes": {"temperature": 25.0, "wind_speed": 3}}
        image_bytes = render_dashboard(ha_data=ha_data, output_format="BMP")
        assert len(image_bytes) > 0


def test_precip_chart_zero_precipitation():
    """Test precipitation chart handles all-zero values without crashing."""
    img = Image.new("RGB", (400, 240), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    forecast_data = [
        {"datetime": f"2026-03-13T{h:02d}:00:00+01:00", "precipitation": 0}
        for h in range(24)
    ]
    # Should not raise
    _draw_precip_chart(draw, forecast_data, origin_x=10, baseline_y=220, chart_w=370, chart_h=80)


def test_precip_chart_missing_precipitation_key():
    """Test precipitation chart handles entries without 'precipitation' key."""
    img = Image.new("RGB", (400, 240), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    forecast_data = [{"datetime": f"2026-03-13T{h:02d}:00:00+01:00"} for h in range(24)]
    _draw_precip_chart(draw, forecast_data, origin_x=10, baseline_y=220, chart_w=370, chart_h=80)


def test_render_dashboard_with_departures():
    """Test rendering with departure data for two directions."""
    departures_display = [
        {
            "line": "340",
            "direction": "Haarlem Stn",
            "times": [
                {"time": "14:03", "delay_min": 0},
                {"time": "14:11", "delay_min": 0},
                {"time": "14:19", "delay_min": 2},
                {"time": "14:26", "delay_min": 0},
            ],
        },
        {
            "line": "340",
            "direction": "Uithoorn Bus",
            "times": [
                {"time": "14:04", "delay_min": 0},
                {"time": "14:12", "delay_min": 0},
                {"time": "14:19", "delay_min": 0},
                {"time": "14:27", "delay_min": 3},
            ],
        },
    ]
    image_bytes = render_dashboard(departures_display=departures_display, output_format="BMP")
    assert len(image_bytes) > 0
    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)


def test_render_dashboard_departures_and_sensors_combined():
    """Test rendering with both departures and sensors in the right panel."""
    departures_display = [
        {
            "line": "340",
            "direction": "Haarlem Stn",
            "times": [{"time": "14:03", "delay_min": 0}],
        }
    ]
    sensors_display = [
        {"label": "Living Room", "value": "21.3", "unit": "°C"},
    ]
    image_bytes = render_dashboard(
        departures_display=departures_display,
        sensors_display=sensors_display,
        output_format="BMP",
    )
    assert len(image_bytes) > 0


def test_render_dashboard_departures_empty_times():
    """Test departure row with no upcoming times shows fallback text."""
    departures_display = [
        {"line": "340", "direction": "Haarlem Stn", "times": []},
    ]
    image_bytes = render_dashboard(departures_display=departures_display, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_departures_with_delay():
    """Test that delayed departures render without crash."""
    departures_display = [
        {
            "line": "340",
            "direction": "Haarlem Stn",
            "times": [
                {"time": "14:03", "delay_min": 5},
                {"time": "14:11", "delay_min": 10},
            ],
        }
    ]
    image_bytes = render_dashboard(departures_display=departures_display, output_format="BMP")
    assert len(image_bytes) > 0
