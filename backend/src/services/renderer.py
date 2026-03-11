"""Dashboard image renderer for 800x480 B/W e-paper display."""

import io
import logging
from datetime import datetime
from typing import Any, Literal, Optional

from PIL import Image, ImageDraw, ImageFont

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
except Exception:
    logger.warning("Could not load system fonts, using default")
    FONT_LARGE = ImageFont.load_default()
    FONT_MEDIUM = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()


def render_dashboard(
    ha_data: Optional[dict[str, Any]] = None,
    influx_data: Optional[dict[str, Any]] = None,
    calendar_data: Optional[list[dict[str, Any]]] = None,
    format: Literal["BMP", "PNG"] = "BMP",
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
    # Create white background image
    image = Image.new("RGB", (DISPLAY_WIDTH, DISPLAY_HEIGHT), color=255)
    draw = ImageDraw.Draw(image)

    # Draw dividing lines
    draw.rectangle([0, 0, DISPLAY_WIDTH, DISPLAY_HEIGHT], outline=0, width=1)
    draw.line([(WEATHER_WIDTH, 0), (WEATHER_WIDTH, CALENDAR_TOP)], fill=0, width=1)
    draw.line([(0, CALENDAR_TOP), (DISPLAY_WIDTH, CALENDAR_TOP)], fill=0, width=1)

    # Draw panels
    _draw_weather_panel(image, draw, ha_data)
    _draw_sensors_panel(image, draw, influx_data)
    _draw_calendar_panel(image, draw, calendar_data)

    # Convert to 1-bit B/W with Floyd-Steinberg dithering
    bw_image = image.convert("1", dither=Image.Dither.FLOYDSTEINBERG)

    # Save to bytes
    output = io.BytesIO()
    bw_image.save(output, format=format)
    output.seek(0)
    logger.info(f"Dashboard rendered: {format} format, {len(output.getvalue())} bytes")
    return output.getvalue()


def _draw_weather_panel(
    image: Image.Image, draw: ImageDraw.ImageDraw, ha_data: Optional[dict[str, Any]]
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
    panel_width = WEATHER_WIDTH - 20

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
        condition = attrs.get("condition", "Unknown").capitalize()
        wind_speed = attrs.get("wind_speed", "N/A")

        # Format temperature string
        if isinstance(temperature, (int, float)):
            temp_str = f"{temperature}°C"
        else:
            temp_str = str(temperature)

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
            f"{condition}",
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
    except Exception as e:
        logger.error(f"Error drawing weather panel: {e}")
        draw.text(
            (panel_x, panel_y),
            "Weather\nError",
            fill=0,
            font=FONT_MEDIUM,
        )


def _draw_sensors_panel(
    image: Image.Image, draw: ImageDraw.ImageDraw, influx_data: Optional[dict[str, Any]]
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
        pressure = influx_data.get("pressure", "N/A")

        # Format strings
        if temperature_avg > -999:
            temp_str = f"Avg Temp: {temperature_avg:.1f}°C"
        else:
            temp_str = "Avg Temp: N/A"

        if humidity_avg > -999:
            humid_str = f"Avg Humidity: {humidity_avg:.0f}%"
        else:
            humid_str = "Avg Humidity: N/A"

        pressure_str = f"Pressure: {pressure} hPa"

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
        draw.text(
            (panel_x, panel_y + 110),
            pressure_str,
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


def _draw_calendar_panel(
    image: Image.Image,
    draw: ImageDraw.ImageDraw,
    calendar_data: Optional[list[dict[str, Any]]],
) -> None:
    """
    Draw calendar panel across bottom of display.

    Args:
        image: PIL Image to draw on
        draw: ImageDraw object
        calendar_data: List of upcoming events (optional)

    Visual:
    - Bottom box: 0-800px wide, 240-480px tall
    - Draw border
    - List next 4 events (one per line) with time + title
    - Format: "09:30 - Standup"
    """
    panel_x, panel_y = 10, CALENDAR_TOP + 10
    max_events = 4

    # Draw title
    draw.text(
        (panel_x, panel_y),
        "Calendar",
        fill=0,
        font=FONT_MEDIUM,
    )

    if not calendar_data or len(calendar_data) == 0:
        draw.text(
            (panel_x, panel_y + 40),
            "No upcoming events",
            fill=0,
            font=FONT_SMALL,
        )
        return

    try:
        # Draw up to 4 events
        for idx, event in enumerate(calendar_data[:max_events]):
            y_offset = panel_y + 40 + (idx * 40)

            # Extract event data
            summary = event.get("summary", "Untitled")
            start_str = event.get("start", "")

            # Parse time from ISO format (e.g., "2026-03-10T09:30:00+01:00")
            try:
                if "T" in start_str:
                    # Extract time part (HH:MM)
                    time_part = start_str.split("T")[1][:5]  # "09:30"
                else:
                    time_part = "TBD"
            except Exception:
                time_part = "TBD"

            # Format event line
            event_line = f"{time_part} - {summary[:40]}"
            draw.text(
                (panel_x, y_offset),
                event_line,
                fill=0,
                font=FONT_SMALL,
            )
    except Exception as e:
        logger.error(f"Error drawing calendar panel: {e}")
        draw.text(
            (panel_x, panel_y + 40),
            "Calendar error",
            fill=0,
            font=FONT_SMALL,
        )
