"""Display endpoints for BMP/PNG rendering."""

import logging
from typing import Annotated
from zoneinfo import ZoneInfo

import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from src.config import settings
from src.fetchers.google_calendar import GoogleCalendarClient
from src.fetchers.home_assistant import HomeAssistantClient
from src.fetchers.influxdb import InfluxDBClient
from src.services.cache import TTLCache
from src.services.renderer import render_dashboard

logger = logging.getLogger(__name__)

router = APIRouter(tags=["display"])


async def _fetch_dashboard_data(
    cache: TTLCache, http_client: httpx.AsyncClient, force_refresh: bool = False
) -> tuple[dict, dict, list]:
    """Fetch and cache data from all sources."""
    ha_data = {}
    influx_data = {}
    calendar_data = []

    # Force refresh if requested
    if force_refresh:
        await cache.invalidate("ha")
        await cache.invalidate("influxdb")
        await cache.invalidate("calendar")

    # Fetch Home Assistant data
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

    return ha_data, influx_data, calendar_data


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
        ha_data, influx_data, calendar_data = await _fetch_dashboard_data(
            cache, http_client, force_refresh
        )
        tz = ZoneInfo(settings.display_timezone)
        image_bytes = render_dashboard(ha_data, influx_data, calendar_data, output_format="BMP", display_tz=tz, invert=settings.display_invert)
        return Response(content=image_bytes, media_type="image/bmp")
    except Exception as e:
        logger.error(f"Error rendering BMP: {e}")
        # Return placeholder "No Data" image
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
        ha_data, influx_data, calendar_data = await _fetch_dashboard_data(
            cache, http_client, force_refresh
        )
        tz = ZoneInfo(settings.display_timezone)
        image_bytes = render_dashboard(ha_data, influx_data, calendar_data, output_format="PNG", display_tz=tz, invert=settings.display_invert)
        return Response(content=image_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"Error rendering PNG: {e}")
        # Return placeholder "No Data" image
        placeholder = render_dashboard(None, None, None, output_format="PNG")
        return Response(content=placeholder, media_type="image/png")
