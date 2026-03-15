"""Tests for dashboard renderer."""

from datetime import UTC, datetime, timedelta
from io import BytesIO
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

from src.services.renderer import (
    _draw_precip_chart,
    _draw_sun_arc,
    _event_time_str,
    _parse_event_dt,
    _wrap_text,
    render_dashboard,
)


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


def test_render_dashboard_no_invert():
    """Test rendering with invert=False."""
    image_bytes = render_dashboard(None, None, None, output_format="BMP", invert=False)
    assert image_bytes[:2] == b"BM"
    img = Image.open(BytesIO(image_bytes))
    assert img.size == (800, 480)


def test_render_dashboard_with_sun_data():
    """Test rendering with sun rise/set data."""
    now = datetime.now(UTC)
    sun_data = {
        "attributes": {
            "next_rising": (now + timedelta(hours=6)).isoformat(),
            "next_setting": (now + timedelta(hours=18)).isoformat(),
        }
    }
    ha_data = {"state": "sunny", "attributes": {"temperature": 20.0, "wind_speed": 5}}
    image_bytes = render_dashboard(ha_data=ha_data, sun_data=sun_data, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_with_quote():
    """Test rendering with a quote string."""
    image_bytes = render_dashboard(
        None, None, None,
        output_format="BMP",
        quote="The sun is generous today."
    )
    assert len(image_bytes) > 0


# ── _draw_sun_arc ──────────────────────────────────────────────────────────────

def _make_draw():
    img = Image.new("RGB", (400, 100), color=(255, 255, 255))
    return img, ImageDraw.Draw(img)


def test_draw_sun_arc_normal():
    """Should draw without raising."""
    tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    sunrise = now - timedelta(hours=4)
    sunset = now + timedelta(hours=4)
    _, draw = _make_draw()
    _draw_sun_arc(draw, sunrise, sunset, now, origin_x=10, origin_y=10, width=380, height=60)


def test_draw_sun_arc_zero_duration():
    """sunrise == sunset — should not raise (total_s <= 0 branch)."""
    tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    _, draw = _make_draw()
    _draw_sun_arc(draw, now, now, now, origin_x=10, origin_y=10, width=380, height=60)


def test_draw_sun_arc_past_sunset():
    """now > sunset — progress clamped to 1.0."""
    tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    sunrise = now - timedelta(hours=10)
    sunset = now - timedelta(hours=2)
    _, draw = _make_draw()
    _draw_sun_arc(draw, sunrise, sunset, now, origin_x=10, origin_y=10, width=380, height=60)


def test_draw_sun_arc_before_sunrise():
    """now < sunrise — progress clamped to 0.0."""
    tz = ZoneInfo("UTC")
    now = datetime.now(tz)
    sunrise = now + timedelta(hours=2)
    sunset = now + timedelta(hours=10)
    _, draw = _make_draw()
    _draw_sun_arc(draw, sunrise, sunset, now, origin_x=10, origin_y=10, width=380, height=60)


# ── _parse_event_dt ────────────────────────────────────────────────────────────

def test_parse_event_dt_datetime_with_tz():
    tz = ZoneInfo("Europe/Amsterdam")
    result = _parse_event_dt("2026-03-15T10:00:00+01:00", tz)
    assert result is not None
    assert result.hour == 10


def test_parse_event_dt_datetime_naive():
    tz = ZoneInfo("Europe/Amsterdam")
    result = _parse_event_dt("2026-03-15T10:00:00", tz)
    assert result is not None


def test_parse_event_dt_all_day():
    tz = ZoneInfo("Europe/Amsterdam")
    result = _parse_event_dt("2026-03-15", tz)
    assert result is not None
    assert result.hour == 0
    assert result.minute == 0


def test_parse_event_dt_empty():
    tz = ZoneInfo("UTC")
    assert _parse_event_dt("", tz) is None


def test_parse_event_dt_invalid():
    tz = ZoneInfo("UTC")
    assert _parse_event_dt("not-a-date", tz) is None


# ── _wrap_text ─────────────────────────────────────────────────────────────────

def test_wrap_text_no_wrap():
    img = Image.new("RGB", (800, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    lines = _wrap_text(draw, "Hi", font, max_width=200)
    assert lines == ["Hi"]


def test_wrap_text_multiline():
    img = Image.new("RGB", (800, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    long_text = "This is a very long sentence that should wrap onto multiple lines when constrained"
    lines = _wrap_text(draw, long_text, font, max_width=50)
    assert len(lines) > 1


def test_wrap_text_single_long_word():
    """A single word longer than max_width still returns a list."""
    img = Image.new("RGB", (800, 100))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    lines = _wrap_text(draw, "Superlongwordthatcannotwrap", font, max_width=1)
    assert len(lines) >= 1


# ── _event_time_str ────────────────────────────────────────────────────────────

def test_event_time_str_all_day():
    result = _event_time_str(None, "2026-03-15")
    assert result == "all day"


def test_event_time_str_timed():
    tz = ZoneInfo("UTC")
    dt = datetime(2026, 3, 15, 14, 30, tzinfo=tz)
    result = _event_time_str(dt, "2026-03-15T14:30:00+00:00")
    assert result == "14:30"


def test_event_time_str_timed_none_dt():
    """If dt is None but start has T, return '?'."""
    result = _event_time_str(None, "2026-03-15T14:30:00+00:00")
    assert result == "?"


# ── Additional renderer tests for coverage ─────────────────────────────────────

def test_precip_chart_empty_list():
    """Empty forecast_data → early return, no crash."""
    img = Image.new("RGB", (400, 240), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    _draw_precip_chart(draw, [], origin_x=10, baseline_y=220, chart_w=370, chart_h=80)


def test_precip_chart_invalid_datetime():
    """Entry with invalid datetime string falls back to index label."""
    img = Image.new("RGB", (400, 240), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # 24 entries where datetime is bad — hits the except branch for label fallback
    forecast_data = [{"datetime": "BAD", "precipitation": 1.0} for _ in range(24)]
    _draw_precip_chart(draw, forecast_data, origin_x=10, baseline_y=220, chart_w=370, chart_h=80)


def test_render_dashboard_with_calendar_next_days():
    """Calendar with events in tomorrow and day+2 exercises the next-days section."""
    today = datetime.now(ZoneInfo("UTC")).date()
    tomorrow = today + timedelta(days=1)
    day2 = today + timedelta(days=2)
    calendar_data = [
        {
            "summary": "Meeting tomorrow",
            "start": f"{tomorrow}T09:00:00+00:00",
            "end": f"{tomorrow}T10:00:00+00:00",
        },
        {
            "summary": "Event day2",
            "start": f"{day2}T14:00:00+00:00",
            "end": f"{day2}T15:00:00+00:00",
        },
    ]
    image_bytes = render_dashboard(
        calendar_data=calendar_data,
        output_format="BMP",
        display_tz=ZoneInfo("UTC"),
    )
    assert len(image_bytes) > 0


def test_render_dashboard_with_today_events():
    """Calendar with today's events exercises the today event-drawing loop."""
    today = datetime.now(ZoneInfo("UTC")).date()
    calendar_data = [
        {
            "summary": "Today meeting",
            "start": f"{today}T10:00:00+00:00",
            "end": f"{today}T11:00:00+00:00",
        },
        {
            "summary": "Afternoon slot",
            "start": f"{today}T15:00:00+00:00",
            "end": f"{today}T16:00:00+00:00",
        },
    ]
    image_bytes = render_dashboard(
        calendar_data=calendar_data,
        output_format="BMP",
        display_tz=ZoneInfo("UTC"),
        quote="A quote for today.",
    )
    assert len(image_bytes) > 0


def test_render_dashboard_sun_arc_sunset_before_sunrise():
    """Sun data where sunset < sunrise exercises the day-shift branch (line 337)."""
    now = datetime.now(UTC)
    # next_setting is before next_rising — triggers sunset -= timedelta(days=1)
    sun_data = {
        "attributes": {
            "next_rising": (now + timedelta(hours=6)).isoformat(),
            "next_setting": (now + timedelta(hours=3)).isoformat(),  # before rising
        }
    }
    ha_data = {"state": "sunny", "attributes": {"temperature": 20.0, "wind_speed": 5}}
    image_bytes = render_dashboard(ha_data=ha_data, sun_data=sun_data, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_sun_arc_far_future_sunrise():
    """Sunrise > now + 18h triggers roll-back-one-day branch (lines 340-341)."""
    now = datetime.now(UTC)
    # next_rising is more than 18h in the future
    sun_data = {
        "attributes": {
            "next_rising": (now + timedelta(hours=20)).isoformat(),
            "next_setting": (now + timedelta(hours=28)).isoformat(),
        }
    }
    ha_data = {"state": "sunny", "attributes": {"temperature": 20.0, "wind_speed": 5}}
    image_bytes = render_dashboard(ha_data=ha_data, sun_data=sun_data, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_sun_arc_invalid_string():
    """Bad ISO string in sun data triggers exception branch (lines 350-352)."""
    sun_data = {
        "attributes": {
            "next_rising": "not-a-datetime",
            "next_setting": "also-bad",
        }
    }
    ha_data = {"state": "sunny", "attributes": {"temperature": 20.0, "wind_speed": 5}}
    image_bytes = render_dashboard(ha_data=ha_data, sun_data=sun_data, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_many_departures_overflow():
    """Many departure rows cause y + 36 > bottom branch (line 401)."""
    # Fill up the departures panel with many entries so the overflow check triggers
    departures_display = [
        {"line": str(i), "direction": f"Dir {i}", "times": [{"time": "14:00", "delay_min": 0}]}
        for i in range(20)  # way more than the panel can hold
    ]
    image_bytes = render_dashboard(departures_display=departures_display, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_mdi_none_departures():
    """With MDI font returning None, departure section uses fallback text branch (line 412)."""
    import unittest.mock as mock
    departures_display = [
        {"line": "340", "direction": "Haarlem", "times": [{"time": "14:03", "delay_min": 0}]}
    ]
    with mock.patch("src.services.renderer._ensure_mdi_font", return_value=None):
        image_bytes = render_dashboard(departures_display=departures_display, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_sensors_overflow():
    """Many sensors cause y >= bottom check to trigger (line 467)."""
    sensors_display = [
        {"label": f"Sensor {i}", "value": "21", "unit": "°C"}
        for i in range(30)  # more than the panel can hold
    ]
    image_bytes = render_dashboard(sensors_display=sensors_display, output_format="BMP")
    assert len(image_bytes) > 0


def test_render_dashboard_calendar_all_three_next_days():
    """Events in tomorrow + day+2 + day+3 exercises separator branch (line 650)."""
    today = datetime.now(ZoneInfo("UTC")).date()
    calendar_data = []
    for offset in range(1, 4):
        d = today + timedelta(days=offset)
        calendar_data.append({
            "summary": f"Event day+{offset}",
            "start": f"{d}T10:00:00+00:00",
            "end": f"{d}T11:00:00+00:00",
        })
    image_bytes = render_dashboard(
        calendar_data=calendar_data,
        output_format="BMP",
        display_tz=ZoneInfo("UTC"),
    )
    assert len(image_bytes) > 0
