"""Display endpoints for BMP/PNG rendering."""

import logging
from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from src.config import load_departure_configs, load_sensor_configs, settings
from src.fetchers.google_calendar import GoogleCalendarClient
from src.fetchers.home_assistant import HomeAssistantClient
from src.fetchers.influxdb import InfluxDBClient
from src.services.cache import TTLCache
from src.services.quote import QuoteContext, get_quote
from src.services.renderer import render_dashboard

_sensor_configs = load_sensor_configs()
_departure_configs = load_departure_configs()

logger = logging.getLogger(__name__)

router = APIRouter(tags=["display"])

# Short TTL for departure data — bus times change every few minutes
_CACHE_TTL_DEPARTURES = 60


def _build_sensors_display(
    sensor_configs: list, sensor_entities: list[dict]
) -> list[dict]:
    """Convert raw HA entity states + sensor configs into display-ready dicts."""
    result = []
    binary_device_class_map = {
        "door": ("Open", "Closed"),
        "window": ("Open", "Closed"),
        "motion": ("Motion", "Clear"),
        "lock": ("Unlocked", "Locked"),
        "presence": ("Home", "Away"),
        "occupancy": ("Occupied", "Clear"),
        "plug": ("On", "Off"),
        "smoke": ("Alarm", "Clear"),
    }
    for cfg, entity in zip(sensor_configs, sensor_entities):
        if not entity or "error" in entity:
            continue
        attrs = entity.get("attributes", {})
        raw = entity.get("state", "unavailable")
        if raw == "unavailable":
            result.append({"label": cfg.label, "value": "N/A", "unit": ""})
            continue
        unit = cfg.unit or attrs.get("unit_of_measurement", "")
        device_class = attrs.get("device_class", "")
        if raw in ("on", "off"):
            on_lbl, off_lbl = binary_device_class_map.get(device_class, ("On", "Off"))
            result.append({"label": cfg.label, "value": on_lbl if raw == "on" else off_lbl, "unit": ""})
        else:
            result.append({"label": cfg.label, "value": raw, "unit": unit})
    return result


def _build_departures_display(
    departure_configs: list, departure_entities: list[dict], tz: ZoneInfo
) -> list[dict]:
    """
    Convert raw HA departure sensor states into display-ready departure dicts.

    Returns a list of:
      {
        "line": "340",
        "direction": "Haarlem Station",   # from attrs or short_direction override
        "times": [
          {"time": "14:03", "delay_min": 0},
          ...
        ]
      }
    """
    result = []
    for cfg, entity in zip(departure_configs, departure_entities):
        if not entity or "error" in entity:
            continue
        attrs = entity.get("attributes", {})
        line = attrs.get("line_name", "?")
        direction = cfg.short_direction or attrs.get("direction", "?")
        raw_times = attrs.get("times", [])

        times = []
        now = datetime.now(tz)
        for entry in raw_times:
            planned_str = entry.get("planned", "")
            estimated_str = entry.get("estimated", planned_str)
            try:
                planned_dt = datetime.fromisoformat(planned_str).astimezone(tz)
                estimated_dt = datetime.fromisoformat(estimated_str).astimezone(tz)
            except (ValueError, TypeError):
                continue
            # Skip departures in the past
            if planned_dt < now:
                continue
            delay_min = max(0, round((estimated_dt - planned_dt).total_seconds() / 60))
            times.append({"time": planned_dt.strftime("%H:%M"), "delay_min": delay_min})
            if len(times) >= cfg.max_departures:
                break

        result.append({"line": line, "direction": direction, "times": times})
    return result


async def _fetch_dashboard_data(
    cache: TTLCache, http_client: httpx.AsyncClient, tz: ZoneInfo, force_refresh: bool = False
) -> tuple[dict, dict, list, list, list, list]:
    """Fetch and cache data from all sources."""
    ha_data = {}
    influx_data = {}
    calendar_data = []
    forecast_data: list = []
    sensors_display: list = []
    departures_display: list = []

    if force_refresh:
        for key in ("ha", "ha_forecast", "ha_sensors", "ha_departures", "influxdb", "calendar"):
            await cache.invalidate(key)

    # Fetch Home Assistant weather
    ha_lock = await cache.acquire_lock("ha")
    async with ha_lock:
        ha_data = await cache.get("ha")
        if ha_data is None:
            ha_client = HomeAssistantClient(settings.ha_url, settings.ha_token, http_client)
            ha_data = await ha_client.get_sensor_data("weather.home")
            await cache.set("ha", ha_data, settings.cache_ttl_ha)
            logger.info("Fetched fresh HA data")
        else:
            logger.info("Using cached HA data")

    # Fetch weather forecast
    forecast_lock = await cache.acquire_lock("ha_forecast")
    async with forecast_lock:
        forecast_data = await cache.get("ha_forecast")
        if forecast_data is None:
            ha_client = HomeAssistantClient(settings.ha_url, settings.ha_token, http_client)
            forecast_data = await ha_client.get_weather_forecast("weather.home")
            await cache.set("ha_forecast", forecast_data, settings.cache_ttl_ha)
            logger.info(f"Fetched fresh forecast: {len(forecast_data)} entries")
        else:
            logger.info("Using cached forecast data")

    # Fetch configurable sensor states
    if _sensor_configs:
        sensors_lock = await cache.acquire_lock("ha_sensors")
        async with sensors_lock:
            sensor_entities = await cache.get("ha_sensors")
            if sensor_entities is None:
                ha_client = HomeAssistantClient(settings.ha_url, settings.ha_token, http_client)
                sensor_entities = await ha_client.get_sensor_states(
                    [s.entity_id for s in _sensor_configs]
                )
                await cache.set("ha_sensors", sensor_entities, settings.cache_ttl_ha)
                logger.info(f"Fetched fresh sensor states: {len(sensor_entities)} entities")
            else:
                logger.info("Using cached sensor states")
        sensors_display = _build_sensors_display(_sensor_configs, sensor_entities)

    # Fetch departure sensor states (short TTL — bus times update frequently)
    if _departure_configs:
        dep_lock = await cache.acquire_lock("ha_departures")
        async with dep_lock:
            dep_entities = await cache.get("ha_departures")
            if dep_entities is None:
                ha_client = HomeAssistantClient(settings.ha_url, settings.ha_token, http_client)
                dep_entities = await ha_client.get_sensor_states(
                    [d.entity_id for d in _departure_configs]
                )
                await cache.set("ha_departures", dep_entities, _CACHE_TTL_DEPARTURES)
                logger.info(f"Fetched fresh departure states: {len(dep_entities)} sensors")
            else:
                logger.info("Using cached departure states")
        departures_display = _build_departures_display(_departure_configs, dep_entities, tz)

    # Fetch InfluxDB data
    influx_lock = await cache.acquire_lock("influxdb")
    async with influx_lock:
        influx_data = await cache.get("influxdb")
        if influx_data is None:
            influx_client = InfluxDBClient(
                settings.influxdb_url,
                settings.influxdb_token,
                settings.influxdb_bucket,
                settings.influxdb_org,
                http_client,
            )
            temp_avg = await influx_client.query_temperature_avg("1h")
            humid_avg = await influx_client.query_humidity_avg("1h")
            influx_data = {
                "temperature_avg": temp_avg,
                "humidity_avg": humid_avg,
            }
            await cache.set("influxdb", influx_data, settings.cache_ttl_influxdb)
            logger.info("Fetched fresh InfluxDB data")
        else:
            logger.info("Using cached InfluxDB data")

    # Fetch Google Calendar data
    calendar_lock = await cache.acquire_lock("calendar")
    async with calendar_lock:
        calendar_data = await cache.get("calendar")
        if calendar_data is None:
            calendar_client = GoogleCalendarClient(
                settings.google_service_account_json, http_client
            )
            calendar_data = await calendar_client.get_upcoming_events(max_results=20)
            await cache.set("calendar", calendar_data, settings.cache_ttl_calendar)
            logger.info("Fetched fresh calendar data")
        else:
            logger.info("Using cached calendar data")

    return ha_data, influx_data, calendar_data, forecast_data, sensors_display, departures_display


@router.get("/display.bmp")
async def get_display_bmp(
    request: Request,
    force_refresh: Annotated[bool, Query()] = False,
) -> Response:
    """
    Render and return 800x480 B/W BMP image.

    Query params:
    - force_refresh: Invalidate cache and fetch fresh data
    """
    app = request.app
    cache: TTLCache = app.state.cache
    http_client: httpx.AsyncClient = app.state.http_client

    try:
        tz = ZoneInfo(settings.display_timezone)
        ha_data, influx_data, calendar_data, forecast_data, sensors_display, departures_display = (
            await _fetch_dashboard_data(cache, http_client, tz, force_refresh)
        )
        condition = ha_data.get("state") if ha_data and "error" not in ha_data else None
        temperature = (ha_data.get("attributes", {}).get("temperature") if ha_data else None)
        quote = get_quote(QuoteContext(
            today=datetime.now(tz).date(),
            weather_condition=condition,
            temperature=float(temperature) if temperature is not None else None,
            language=settings.quote_language,
        ))
        image_bytes = render_dashboard(
            ha_data, influx_data, calendar_data,
            output_format="BMP", display_tz=tz, invert=settings.display_invert,
            forecast_data=forecast_data, sensors_display=sensors_display,
            departures_display=departures_display, quote=quote,
        )
        return Response(content=image_bytes, media_type="image/bmp")
    except Exception as e:
        logger.error(f"Error rendering BMP: {e}")
        placeholder = render_dashboard(None, None, None, output_format="BMP")
        return Response(content=placeholder, media_type="image/bmp")


@router.get("/display.png")
async def get_display_png(
    request: Request,
    force_refresh: Annotated[bool, Query()] = False,
) -> Response:
    """
    Render and return 800x480 B/W PNG image.

    Query params:
    - force_refresh: Invalidate cache and fetch fresh data
    """
    app = request.app
    cache: TTLCache = app.state.cache
    http_client: httpx.AsyncClient = app.state.http_client

    try:
        tz = ZoneInfo(settings.display_timezone)
        ha_data, influx_data, calendar_data, forecast_data, sensors_display, departures_display = (
            await _fetch_dashboard_data(cache, http_client, tz, force_refresh)
        )
        condition = ha_data.get("state") if ha_data and "error" not in ha_data else None
        temperature = (ha_data.get("attributes", {}).get("temperature") if ha_data else None)
        quote = get_quote(QuoteContext(
            today=datetime.now(tz).date(),
            weather_condition=condition,
            temperature=float(temperature) if temperature is not None else None,
            language=settings.quote_language,
        ))
        image_bytes = render_dashboard(
            ha_data, influx_data, calendar_data,
            output_format="PNG", display_tz=tz, invert=settings.display_invert,
            forecast_data=forecast_data, sensors_display=sensors_display,
            departures_display=departures_display, quote=quote,
        )
        return Response(content=image_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Error rendering PNG: {e}")
        placeholder = render_dashboard(None, None, None, output_format="PNG")
        return Response(content=placeholder, media_type="image/png")
