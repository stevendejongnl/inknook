"""Dashboard image renderer for 800x480 B/W e-paper display."""

import io
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont, ImageOps

_DEFAULT_TZ = ZoneInfo("Europe/Amsterdam")

logger = logging.getLogger(__name__)

# Display dimensions
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

# Layout constants
WEATHER_WIDTH = 400
SENSORS_WIDTH = 400
CALENDAR_TOP = 240
BOTTOM_BAR_HEIGHT = 32  # Reserved for ESPHome-drawn status bar

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
    invert: bool = True,
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
    draw.line([(WEATHER_WIDTH, 0), (WEATHER_WIDTH, CALENDAR_TOP)], fill=0, width=1)
    draw.line([(0, CALENDAR_TOP), (DISPLAY_WIDTH, CALENDAR_TOP)], fill=0, width=1)
    # Separator above bottom bar (ESPHome draws the bar contents over this region)
    draw.line(
        [(0, DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT), (DISPLAY_WIDTH, DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT)],
        fill=0,
        width=1,
    )

    tz = display_tz or _DEFAULT_TZ

    # Draw panels
    _draw_weather_panel(image, draw, ha_data)
    _draw_sensors_panel(image, draw, influx_data)
    _draw_calendar_panel(image, draw, calendar_data, tz)

    # Convert to 1-bit. Optionally invert for e-paper drivers that read
    # 0=white/1=black (opposite of PIL's 0=black/1=white convention).
    gray = image.convert("L")
    if invert:
        gray = ImageOps.invert(gray)
    bw_image = gray.convert("1", dither=Image.Dither.NONE)

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


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Word-wrap text to fit within max_width pixels."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = (current + " " + word).strip()
        if draw.textlength(candidate, font=font) > max_width and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [text]


def _event_time_str(dt: datetime | None, start_raw: str) -> str:
    if "T" not in start_raw:
        return "all day"
    return dt.strftime("%H:%M") if dt else "?"


def _draw_event(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    dt: datetime | None,
    event: dict[str, Any],
    max_width: int,
    bottom_limit: int,
) -> int:
    """Draw one event (bold time + wrapped name). Returns new y position."""
    time_str = _event_time_str(dt, event.get("start", ""))
    summary = event.get("summary", "Untitled")

    time_w = int(draw.textlength(time_str, font=FONT_TINY_BOLD)) + 5
    draw.text((x, y), time_str, fill=0, font=FONT_TINY_BOLD)

    name_x = x + time_w
    name_max = max_width - time_w
    lines = _wrap_text(draw, summary, FONT_TINY, name_max)
    for i, line in enumerate(lines):
        if y >= bottom_limit:
            break
        draw.text((name_x if i == 0 else x + time_w, y), line, fill=0, font=FONT_TINY)
        if i < len(lines) - 1:
            y += 18
    return y + 19


def _draw_calendar_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    calendar_data: list[dict[str, Any]] | None,
    tz: ZoneInfo,
) -> None:
    """
    Calendar panel: left half = today (full height), right half = next 3 days stacked.

    Layout:
    - Left  (0–399px):   Today's events with text wrapping
    - Right (401–799px): Tomorrow / day+2 / day+3 in equal thirds
    - Vertical divider at x=400
    - Bold times, wrapped event names
    """
    top = CALENDAR_TOP + 8
    bottom = DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT - 4  # 444px — leave space for status bar
    mid = DISPLAY_WIDTH // 2  # 400

    # Vertical divider between today and upcoming (stops at bottom bar)
    draw.line([(mid, CALENDAR_TOP), (mid, DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT)], fill=0, width=1)

    # Group events by local date
    today = datetime.now(tz).date()
    by_day: dict[date, list[tuple[datetime | None, dict]]] = {
        today + timedelta(days=i): [] for i in range(4)
    }
    if calendar_data:
        for event in calendar_data:
            dt = _parse_event_dt(event.get("start", ""), tz)
            if dt and dt.date() in by_day:
                by_day[dt.date()].append((dt, event))

    # ── Left: Today ──────────────────────────────────────────────────────────
    lx = 8
    ly = top
    lw = mid - lx - 8  # usable width ~384px

    draw.text((lx, ly), "Today", fill=0, font=FONT_TINY_BOLD)
    ly += 18
    draw.line([(lx, ly), (mid - 8, ly)], fill=0, width=1)
    ly += 5

    today_events = by_day[today]
    if not today_events:
        draw.text((lx, ly), "Nothing to do today", fill=0, font=FONT_TINY)
    else:
        for dt, event in today_events:
            if ly >= bottom - 18:
                break
            ly = _draw_event(draw, lx, ly, dt, event, lw, bottom)

    # ── Right: Next days with events (skip empty days) ───────────────────────
    rx = mid + 8
    rw = DISPLAY_WIDTH - rx - 5  # usable width ~387px

    # Only show days that have events
    next_days = [
        today + timedelta(days=i)
        for i in range(1, 4)
        if by_day[today + timedelta(days=i)]
    ]

    if not next_days:
        draw.text((rx, top), "No upcoming events", fill=0, font=FONT_TINY)
    else:
        section_h = (DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT - CALENDAR_TOP) // len(next_days)
        for idx, day in enumerate(next_days):
            sy = CALENDAR_TOP + idx * section_h + 6
            sec_bottom = CALENDAR_TOP + (idx + 1) * section_h - 4

            # Day label
            if day == today + timedelta(days=1):
                label = f"Tomorrow  {day.strftime('%-d %b')}"
            else:
                label = day.strftime("%A  %-d %b")
            draw.text((rx, sy), label, fill=0, font=FONT_TINY_BOLD)
            sy += 18

            for dt, event in by_day[day]:
                if sy >= sec_bottom:
                    break
                sy = _draw_event(draw, rx, sy, dt, event, rw, sec_bottom)

            # Separator between sections (not after last)
            if idx < len(next_days) - 1:
                sep_y = CALENDAR_TOP + (idx + 1) * section_h
                draw.line([(rx, sep_y), (DISPLAY_WIDTH - 5, sep_y)], fill=0, width=1)
