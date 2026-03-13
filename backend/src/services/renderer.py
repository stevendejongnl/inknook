"""Dashboard image renderer for 800x480 B/W e-paper display."""

import io
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

_DEFAULT_TZ = ZoneInfo("Europe/Amsterdam")

logger = logging.getLogger(__name__)

# Display dimensions
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# Layout constants
WEATHER_WIDTH = 400
SENSORS_WIDTH = 400
CALENDAR_TOP = 240

# Try to load a system font, fallback to default
try:
    FONT_LARGE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    FONT_MEDIUM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    FONT_SMALL = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    FONT_TINY = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    FONT_TINY_BOLD = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
except Exception:
    logger.warning("Could not load system fonts, using default")
    FONT_LARGE = ImageFont.load_default()
    FONT_MEDIUM = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()
    FONT_TINY = ImageFont.load_default()
    FONT_TINY_BOLD = ImageFont.load_default()


def render_dashboard(
    ha_data: dict[str, Any] | None = None,
    influx_data: dict[str, Any] | None = None,
    calendar_data: list[dict[str, Any]] | None = None,
    output_format: Literal["BMP", "PNG"] = "BMP",
    display_tz: ZoneInfo | None = None,
) -> bytes:
    """
    Render 800x480 B/W dashboard from sensor and calendar data.

    Args:
        ha_data: Home Assistant sensor data with temperature, humidity, condition
        influx_data: InfluxDB aggregated data with temperature_avg, humidity_avg
        calendar_data: List of upcoming events with summary, start, end
        format: Output format ('BMP' or 'PNG')

    Returns:
        Image bytes in specified format

    Layout (800x480):
    - Top-left (0-400px wide): Weather panel
      - Current temperature from HA
      - Condition (cloudy, sunny, etc.)
      - Wind speed
    - Top-right (400-800px wide): Sensors panel
      - Average temperature from InfluxDB
      - Average humidity from InfluxDB
      - Pressure from HA
    - Bottom (240-480px tall): Calendar panel
      - Next 4 events with time and title

    Graceful degradation:
    - If data missing, show placeholder text
    - If API error, show last cached data
    - If all data missing, show "No Data Available"
    """
    # Create white background image — must pass tuple for RGB, not int
    image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Draw dividing lines
    draw.rectangle([0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT], outline=0, width=1)
    draw.line([(WEATHER_WIDTH, 0), (WEATHER_WIDTH, CALENDAR_TOP)], fill=0, width=1)
    draw.line([(0, CALENDAR_TOP), (DISPLAY_WIDTH, CALENDAR_TOP)], fill=0, width=1)

    tz = display_tz or _DEFAULT_TZ

    # Draw panels
    _draw_weather_panel(image, draw, ha_data)
    _draw_sensors_panel(image, draw, influx_data)
    _draw_calendar_panel(image, draw, calendar_data, tz)

    # Convert to 1-bit B/W — hard threshold, no dithering.
    # Floyd-Steinberg would propagate error from anti-aliased font edges
    # into the white background, creating noise across the whole image.
    bw_image = image.convert("1", dither=Image.Dither.NONE)

    # Save to bytes
    output = io.BytesIO()
    bw_image.save(output, format=output_format)
    output.seek(0)
    logger.info(f"Dashboard rendered: {output_format} format, {len(output.getvalue())} bytes")
    return output.getvalue()


def _draw_weather_panel(
    image: Image.Image, draw: ImageDraw.ImageDraw, ha_data: dict[str, Any] | None
) -> None:
    """
    Draw weather panel on left side of display.

    Args:
        image: PIL Image to draw on
        draw: ImageDraw object
        ha_data: Home Assistant data (optional)

    Visual:
    - Top-left box: 0-400px wide, 0-240px tall
    - Draw border
    - Display temperature (large)
    - Display condition + icon (if available)
    - Display wind speed
    - If no data, show "Weather\nUnavailable"
    """
    panel_x, panel_y = 10, 10

    if not ha_data or "error" in ha_data:
        draw.text(
            (panel_x, panel_y),
            "Weather\nUnavailable",
            fill=0,
            font=FONT_MEDIUM,
        )
        return

    try:
        # Extract data from HA response
        attrs = ha_data.get("attributes", {})
        temperature = attrs.get("temperature", "N/A")
        # Condition is the entity state, not an attribute
        condition = ha_data.get("state", "?").replace("-", " ").capitalize()
        wind_speed = attrs.get("wind_speed", "N/A")
        precipitation = attrs.get("precipitation")
        cloud_coverage = attrs.get("cloud_coverage")

        # Format temperature string
        if isinstance(temperature, (int, float)):
            temp_str = f"{temperature}°C"
        else:
            temp_str = str(temperature)

        # Build rain string: prefer precipitation mm/h, fall back to cloud coverage
        if precipitation is not None:
            rain_str = f"Rain: {precipitation:.1f} mm"
        elif cloud_coverage is not None:
            rain_str = f"Clouds: {cloud_coverage:.0f}%"
        else:
            rain_str = "Rain: --"

        # Draw title
        draw.text(
            (panel_x, panel_y),
            "Weather",
            fill=0,
            font=FONT_MEDIUM,
        )

        # Draw temperature (large)
        draw.text(
            (panel_x, panel_y + 40),
            temp_str,
            fill=0,
            font=FONT_LARGE,
        )

        # Draw condition
        draw.text(
            (panel_x, panel_y + 100),
            condition,
            fill=0,
            font=FONT_SMALL,
        )

        # Draw wind speed
        draw.text(
            (panel_x, panel_y + 130),
            f"Wind: {wind_speed} km/h",
            fill=0,
            font=FONT_SMALL,
        )

        # Draw rain/precipitation
        draw.text(
            (panel_x, panel_y + 160),
            rain_str,
            fill=0,
            font=FONT_SMALL,
        )
    except Exception as e:
        logger.error(f"Error drawing weather panel: {e}")
        draw.text(
            (panel_x, panel_y),
            "Weather\nError",
            fill=0,
            font=FONT_MEDIUM,
        )


def _draw_sensors_panel(
    image: Image.Image, draw: ImageDraw.ImageDraw, influx_data: dict[str, Any] | None
) -> None:
    """
    Draw sensors panel on right side of display.

    Args:
        image: PIL Image to draw on
        draw: ImageDraw object
        influx_data: InfluxDB aggregated data (optional)

    Visual:
    - Top-right box: 400-800px wide, 0-240px tall
    - Draw border
    - Display average temperature
    - Display average humidity
    - Display pressure
    """
    panel_x, panel_y = 410, 10

    if not influx_data:
        draw.text(
            (panel_x, panel_y),
            "Sensors\nUnavailable",
            fill=0,
            font=FONT_MEDIUM,
        )
        return

    try:
        # Extract aggregated sensor data
        temperature_avg = influx_data.get("temperature_avg", -999.0)
        humidity_avg = influx_data.get("humidity_avg", -999.0)

        # Format strings
        if isinstance(temperature_avg, (int, float)) and temperature_avg > -999:
            temp_str = f"Avg Temp: {temperature_avg:.1f}°C"
        else:
            temp_str = "Avg Temp: N/A"

        if isinstance(humidity_avg, (int, float)) and humidity_avg > -999:
            humid_str = f"Avg Humidity: {humidity_avg:.0f}%"
        else:
            humid_str = "Avg Humidity: N/A"

        # Draw title
        draw.text(
            (panel_x, panel_y),
            "Sensors",
            fill=0,
            font=FONT_MEDIUM,
        )

        # Draw sensor values
        draw.text(
            (panel_x, panel_y + 50),
            temp_str,
            fill=0,
            font=FONT_SMALL,
        )
        draw.text(
            (panel_x, panel_y + 80),
            humid_str,
            fill=0,
            font=FONT_SMALL,
        )
    except Exception as e:
        logger.error(f"Error drawing sensors panel: {e}")
        draw.text(
            (panel_x, panel_y),
            "Sensors\nError",
            fill=0,
            font=FONT_MEDIUM,
        )


def _parse_event_dt(start_str: str, tz: ZoneInfo) -> datetime | None:
    """Parse event start string to local datetime."""
    try:
        if not start_str:
            return None
        if "T" in start_str:
            dt = datetime.fromisoformat(start_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(tz)
        else:
            # All-day event: treat as midnight local time
            d = date.fromisoformat(start_str)
            return datetime(d.year, d.month, d.day, tzinfo=tz)
    except (ValueError, TypeError):
        return None


def _day_label(d: date, tz: ZoneInfo) -> str:
    """Return 'Today', 'Tomorrow', or short weekday + date."""
    today = datetime.now(tz).date()
    if d == today:
        return f"Today  {d.strftime('%-d %b')}"
    if d == today + timedelta(days=1):
        return f"Tomorrow  {d.strftime('%-d %b')}"
    return d.strftime("%a  %-d %b")


def _draw_calendar_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    calendar_data: list[dict[str, Any]] | None,
    tz: ZoneInfo,
) -> None:
    """
    Draw calendar panel across bottom of display.

    4-column layout, one column per day (today + 3 days).
    Each column shows a day header and up to ~8 events.
    Times are shown in Amsterdam local time.
    """
    panel_y = CALENDAR_TOP + 8
    col_width = DISPLAY_WIDTH // 4  # 200px per column
    row_h = 20  # pixels per event row
    max_rows = 10  # max events per column

    # Group events by local date
    today = datetime.now(tz).date()
    by_day: dict[date, list[tuple[datetime | None, dict]]] = {}
    for i in range(4):
        by_day[today + timedelta(days=i)] = []

    if calendar_data:
        for event in calendar_data:
            dt = _parse_event_dt(event.get("start", ""), tz)
            if dt is None:
                continue
            d = dt.date()
            if d in by_day:
                by_day[d].append((dt, event))

    # Draw each column
    for col, day in enumerate(sorted(by_day)):
        col_x = col * col_width + 6
        y = panel_y

        # Day header
        label = _day_label(day, tz)
        draw.text((col_x, y), label, fill=0, font=FONT_TINY_BOLD)
        y += row_h + 2
        # Separator line under header
        draw.line([(col_x, y), (col_x + col_width - 10, y)], fill=0, width=1)
        y += 4

        events = by_day[day]
        if not events:
            draw.text((col_x, y), "–", fill=0, font=FONT_TINY)
        else:
            for row_idx, (dt, event) in enumerate(events[:max_rows]):
                summary = event.get("summary", "Untitled")
                start_raw = event.get("start", "")
                is_allday = "T" not in start_raw

                if is_allday:
                    time_str = "allday"
                elif dt:
                    time_str = dt.strftime("%H:%M")
                else:
                    time_str = "?"

                # Truncate summary to fit ~23 chars in 194px @ 16px font
                max_chars = 18
                if len(summary) > max_chars:
                    summary = summary[: max_chars - 1] + "…"

                line = f"{time_str} {summary}"
                draw.text((col_x, y), line, fill=0, font=FONT_TINY)
                y += row_h
