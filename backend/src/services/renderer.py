"""Dashboard image renderer for 800x480 B/W e-paper display."""

import io
import logging
import os
import urllib.request
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

# MDI font loading
_MDI_FONT_CACHE: dict[int, ImageFont.FreeTypeFont] = {}
_MDI_FONT_PATH = "/tmp/inknook_mdi.ttf"
_MDI_FONT_URL = "https://cdn.jsdelivr.net/npm/@mdi/font@7.4.47/fonts/materialdesignicons-webfont.ttf"


def _ensure_mdi_font(size: int) -> ImageFont.FreeTypeFont | None:
    """Load MDI icon font at given size, downloading TTF from CDN if not cached."""
    if size in _MDI_FONT_CACHE:
        return _MDI_FONT_CACHE[size]
    if not os.path.exists(_MDI_FONT_PATH):
        try:
            logger.info("Downloading MDI font from CDN…")
            urllib.request.urlretrieve(_MDI_FONT_URL, _MDI_FONT_PATH)
        except Exception as e:
            logger.warning(f"Failed to download MDI font: {e}")
            return None
    try:
        font = ImageFont.truetype(_MDI_FONT_PATH, size)
        _MDI_FONT_CACHE[size] = font
        return font
    except Exception as e:
        logger.warning(f"Failed to load MDI font: {e}")
        return None


# HA condition string → MDI codepoint (MDI v7)
MDI_CONDITION_GLYPHS: dict[str, str] = {
    "clear-night":    "\U000F0594",  # mdi:weather-night
    "cloudy":         "\U000F0590",  # mdi:weather-cloudy
    "exceptional":    "\U000F0026",  # mdi:alert-circle-outline
    "fog":            "\U000F0591",  # mdi:weather-fog
    "hail":           "\U000F0592",  # mdi:weather-hail
    "lightning":      "\U000F0593",  # mdi:weather-lightning
    "lightning-rainy":"\U000F067E",  # mdi:weather-lightning-rainy
    "partlycloudy":   "\U000F0595",  # mdi:weather-partly-cloudy
    "pouring":        "\U000F0597",  # mdi:weather-pouring
    "rainy":          "\U000F0596",  # mdi:weather-rainy
    "snowy":          "\U000F0F36",  # mdi:weather-snowy
    "snowy-rainy":    "\U000F067F",  # mdi:weather-snowy-rainy
    "sunny":          "\U000F0599",  # mdi:weather-sunny
    "windy":          "\U000F059D",  # mdi:weather-windy
    "windy-variant":  "\U000F059E",  # mdi:weather-windy-variant
}


def render_dashboard(
    ha_data: dict[str, Any] | None = None,
    influx_data: dict[str, Any] | None = None,
    calendar_data: list[dict[str, Any]] | None = None,
    output_format: Literal["BMP", "PNG"] = "BMP",
    display_tz: ZoneInfo | None = None,
    invert: bool = True,
    forecast_data: list[dict[str, Any]] | None = None,
    sensors_display: list[dict[str, Any]] | None = None,
    departures_display: list[dict[str, Any]] | None = None,
) -> bytes:
    """
    Render 800x480 B/W dashboard from sensor and calendar data.

    Layout (800x480):
    - Top-left  (0–400px wide, 0–240px tall): Weather panel
      - MDI condition icon + current temperature + condition + wind
      - 24h precipitation bar chart
    - Top-right (400–800px wide, 0–240px tall): Configurable sensor list
    - Middle+bottom (0–800px wide, 240–448px tall): Calendar panel
    - Bottom bar (448–480px): reserved for ESPHome status bar

    Graceful degradation: missing data → placeholder text
    """
    image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    # Dividing lines
    draw.line([(WEATHER_WIDTH, 0), (WEATHER_WIDTH, CALENDAR_TOP)], fill=0, width=1)
    draw.line([(0, CALENDAR_TOP), (DISPLAY_WIDTH, CALENDAR_TOP)], fill=0, width=1)
    draw.line(
        [(0, DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT), (DISPLAY_WIDTH, DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT)],
        fill=0,
        width=1,
    )

    tz = display_tz or _DEFAULT_TZ

    _draw_weather_panel(image, draw, ha_data, forecast_data)
    _draw_sensors_panel(image, draw, sensors_display, departures_display)
    _draw_calendar_panel(image, draw, calendar_data, tz)

    gray = image.convert("L")
    if invert:
        gray = ImageOps.invert(gray)
    bw_image = gray.convert("1", dither=Image.Dither.NONE)

    output = io.BytesIO()
    bw_image.save(output, format=output_format)
    output.seek(0)
    logger.info(f"Dashboard rendered: {output_format} format, {len(output.getvalue())} bytes")
    return output.getvalue()


def _draw_precip_chart(
    draw: ImageDraw.ImageDraw,
    forecast_data: list[dict[str, Any]],
    origin_x: int = 10,
    baseline_y: int = 220,
    chart_w: int = 378,
    chart_h: int = 85,
) -> None:
    """
    Draw a 24h precipitation bar chart.

    Bars grow upward from baseline_y. Each of the 24 hourly slots is one bar.
    Hour labels (every 4h: 0, 4, 8, 12, 16, 20) are drawn below the baseline.
    """
    entries = forecast_data[:24]
    if not entries:
        return

    n = len(entries)
    bar_w = max(1, chart_w // n)

    # Determine scale: max precipitation in the set, minimum 2mm so bars are visible
    precip_values = [
        float(e.get("precipitation", 0) or 0)
        for e in entries
    ]
    max_precip = max(precip_values) if precip_values else 0
    scale = max(max_precip, 2.0)

    # Axis line (slightly thicker so it's clear at 1-bit)
    draw.line([(origin_x, baseline_y), (origin_x + chart_w, baseline_y)], fill=0, width=2)

    # Bars
    for i, (entry, precip) in enumerate(zip(entries, precip_values)):
        bar_h = int((precip / scale) * chart_h)
        x0 = origin_x + i * bar_w + 1
        x1 = origin_x + (i + 1) * bar_w - 1
        y0 = baseline_y - bar_h
        y1 = baseline_y - 2  # stop 2px above axis so bars don't merge into it
        if bar_h > 0:
            draw.rectangle([x0, y0, x1, y1], fill=0)

    # Hour labels every 4h + scale label on the right, all in the same row
    label_y = baseline_y + 3
    for i, entry in enumerate(entries):
        if i % 4 != 0:
            continue
        dt_str = entry.get("datetime", "")
        label = ""
        try:
            if dt_str:
                dt = datetime.fromisoformat(dt_str)
                label = dt.strftime("%-H")
        except Exception:
            label = str(i)
        x_center = origin_x + i * bar_w + bar_w // 2
        draw.text((x_center - 4, label_y), label, fill=0, font=FONT_TINY)

    # Scale label right-aligned in the time-label row (no overlap with bars)
    if max_precip > 0:
        scale_text = f"{max_precip:.1f}mm"
        scale_w = int(draw.textlength(scale_text, font=FONT_TINY))
        draw.text((origin_x + chart_w - scale_w, label_y), scale_text, fill=0, font=FONT_TINY)


def _draw_weather_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    ha_data: dict[str, Any] | None,
    forecast_data: list[dict[str, Any]] | None = None,
) -> None:
    """
    Draw weather panel: MDI condition icon + temp + condition text + wind,
    then a 24h precipitation bar chart below a divider.

    Panel bounds: x=0–400, y=0–240
    """
    panel_x, panel_y = 10, 10

    if not ha_data or "error" in ha_data:
        draw.text((panel_x, panel_y), "Weather\nUnavailable", fill=0, font=FONT_MEDIUM)
        return

    try:
        attrs = ha_data.get("attributes", {})
        temperature = attrs.get("temperature", "N/A")
        condition_raw = ha_data.get("state", "")
        condition = condition_raw.replace("-", " ").capitalize()
        wind_speed = attrs.get("wind_speed", "N/A")
        wind_unit = attrs.get("wind_speed_unit", "km/h")

        temp_str = f"{temperature}°C" if isinstance(temperature, (int, float)) else str(temperature)

        # MDI condition icon (72pt) at top-left
        mdi_font = _ensure_mdi_font(72)
        glyph = MDI_CONDITION_GLYPHS.get(condition_raw, "\U000F0590")  # fallback: cloudy
        if mdi_font:
            draw.text((panel_x, panel_y), glyph, fill=0, font=mdi_font)
            text_x = panel_x + 82
        else:
            text_x = panel_x

        # Temperature (large) next to icon
        draw.text((text_x, panel_y), temp_str, fill=0, font=FONT_LARGE)

        # Condition and wind below temperature
        draw.text((text_x, panel_y + 58), condition, fill=0, font=FONT_SMALL)
        draw.text((text_x, panel_y + 83), f"Wind: {wind_speed} {wind_unit}", fill=0, font=FONT_SMALL)

        # Divider before chart
        divider_y = panel_y + 113
        draw.line([(panel_x, divider_y), (WEATHER_WIDTH - 10, divider_y)], fill=0, width=1)

        # 24h precipitation bar chart
        if forecast_data:
            _draw_precip_chart(
                draw,
                forecast_data,
                origin_x=panel_x,
                baseline_y=divider_y + 80,  # was 95 — chart sits higher in the panel
                chart_w=WEATHER_WIDTH - panel_x - 10,
                chart_h=70,
            )
        else:
            draw.text((panel_x, divider_y + 8), "No forecast data", fill=0, font=FONT_TINY)

    except Exception as e:
        logger.error(f"Error drawing weather panel: {e}")
        draw.text((panel_x, panel_y), "Weather\nError", fill=0, font=FONT_MEDIUM)


def _draw_departures_section(
    draw: ImageDraw.ImageDraw,
    departures_display: list[dict[str, Any]],
    panel_x: int,
    y: int,
    panel_w: int,
    bottom: int,
) -> int:
    """
    Draw departure rows for each configured direction.

    Each row: "→ <direction>  HH:MM  HH:MM  HH:MM  HH:MM"
    Delayed entries are marked with "+Xm" appended.

    Returns the y position after the last row.
    """
    # Bus icon glyph (mdi:bus = F012E)
    mdi = _ensure_mdi_font(16)
    bus_glyph = "\U000F012E"  # mdi:bus

    for dep in departures_display:
        if y + 36 > bottom:
            break
        line = dep.get("line", "")
        direction = dep.get("direction", "")
        times = dep.get("times", [])

        # Direction header: "[bus] Line → Direction"
        header = f"{line} → {direction}"
        if mdi:
            draw.text((panel_x, y), bus_glyph, fill=0, font=mdi)
            draw.text((panel_x + 20, y), header, fill=0, font=FONT_TINY_BOLD)
        else:
            draw.text((panel_x, y), header, fill=0, font=FONT_TINY_BOLD)
        y += 18

        # Departure times row
        if times:
            parts = []
            for t in times:
                s = t["time"]
                if t.get("delay_min", 0) > 0:
                    s += f"+{t['delay_min']}m"
                parts.append(s)
            draw.text((panel_x + 20, y), "  ".join(parts), fill=0, font=FONT_TINY)
        else:
            draw.text((panel_x + 20, y), "No upcoming departures", fill=0, font=FONT_TINY)
        y += 20

    return y


def _draw_sensors_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    sensors_display: list[dict[str, Any]] | None,
    departures_display: list[dict[str, Any]] | None = None,
) -> None:
    """
    Draw the top-right panel (x=400–800, y=0–240).

    Layout (top to bottom):
    1. Departures section — one row per direction with next departure times
    2. Horizontal divider (if both sections present)
    3. Sensors section — configurable sensor values from sensors.yaml
    """
    panel_x = 410
    panel_w = DISPLAY_WIDTH - panel_x - 5
    bottom = CALENDAR_TOP - 6
    y = 10

    # ── Departures ────────────────────────────────────────────────────────────
    if departures_display:
        y = _draw_departures_section(draw, departures_display, panel_x, y, panel_w, bottom)

        if sensors_display and y + 6 < bottom:
            draw.line([(panel_x, y + 2), (DISPLAY_WIDTH - 10, y + 2)], fill=0, width=1)
            y += 8

    # ── Sensors ───────────────────────────────────────────────────────────────
    if not sensors_display:
        if not departures_display:
            draw.text((panel_x, y), "No data configured", fill=0, font=FONT_TINY)
        return

    line_h = 19
    for sensor in sensors_display:
        if y >= bottom:
            break
        label = sensor.get("label", "")
        value = sensor.get("value", "")
        unit = sensor.get("unit", "")
        value_str = f"{value} {unit}".strip() if unit else value

        label_w = int(draw.textlength(f"{label}: ", font=FONT_TINY_BOLD)) + 1
        draw.text((panel_x, y), f"{label}:", fill=0, font=FONT_TINY_BOLD)
        draw.text((panel_x + label_w, y), value_str, fill=0, font=FONT_TINY)
        y += line_h


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
    bottom = DISPLAY_HEIGHT - BOTTOM_BAR_HEIGHT - 4  # leave space for status bar
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
