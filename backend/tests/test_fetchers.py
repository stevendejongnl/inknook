"""Tests for fetcher clients (HA, InfluxDB, Google Calendar)."""

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.fetchers.home_assistant import HomeAssistantClient
from src.fetchers.influxdb import InfluxDBClient
from src.fetchers.google_calendar import GoogleCalendarClient
from tests.conftest import make_transport


# ── HomeAssistantClient ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ha_get_sensor_data_success(ha_sensor_response):
    transport = make_transport({
        ("GET", "/api/states/weather.home"): httpx.Response(200, json=ha_sensor_response)
    })
    client = httpx.AsyncClient(transport=transport)
    ha = HomeAssistantClient("http://ha:8123", "tok", client)
    result = await ha.get_sensor_data("weather.home")
    assert result["state"] == "cloudy"
    assert result["attributes"]["temperature"] == 18.5


@pytest.mark.asyncio
async def test_ha_get_sensor_data_4xx_no_retry():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(404, text="Not Found")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ha = HomeAssistantClient("http://ha:8123", "tok", client)
    result = await ha.get_sensor_data("sensor.missing")
    assert "error" in result
    assert call_count == 1  # No retry on 4xx


@pytest.mark.asyncio
async def test_ha_get_sensor_data_5xx_retries():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, text="Service Unavailable")

    with patch("asyncio.sleep"):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        ha = HomeAssistantClient("http://ha:8123", "tok", client)
        result = await ha.get_sensor_data("sensor.temp")

    assert "error" in result
    assert call_count == 3  # Retried 3 times


@pytest.mark.asyncio
async def test_ha_get_sensor_data_exception_retries():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("Connection refused")

    with patch("asyncio.sleep"):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        ha = HomeAssistantClient("http://ha:8123", "tok", client)
        result = await ha.get_sensor_data("sensor.temp")

    assert "error" in result
    assert call_count == 3


@pytest.mark.asyncio
async def test_ha_get_weather_forecast_success_wrapped():
    entity_id = "weather.home"
    forecast_data = [{"datetime": "2026-03-15T12:00:00+01:00", "precipitation": 0.5}]
    response_body = {
        "service_response": {
            entity_id: {"forecast": forecast_data}
        }
    }
    transport = make_transport({
        ("POST", "/api/services/weather/get_forecasts"): httpx.Response(200, json=response_body)
    })
    client = httpx.AsyncClient(transport=transport)
    ha = HomeAssistantClient("http://ha:8123", "tok", client)
    result = await ha.get_weather_forecast(entity_id)
    assert len(result) == 1
    assert result[0]["precipitation"] == 0.5


@pytest.mark.asyncio
async def test_ha_get_weather_forecast_success_legacy():
    entity_id = "weather.home"
    forecast_data = [{"datetime": "2026-03-15T12:00:00+01:00", "precipitation": 1.0}]
    response_body = {entity_id: {"forecast": forecast_data}}
    transport = make_transport({
        ("POST", "/api/services/weather/get_forecasts"): httpx.Response(200, json=response_body)
    })
    client = httpx.AsyncClient(transport=transport)
    ha = HomeAssistantClient("http://ha:8123", "tok", client)
    result = await ha.get_weather_forecast(entity_id)
    assert len(result) == 1
    assert result[0]["precipitation"] == 1.0


@pytest.mark.asyncio
async def test_ha_get_weather_forecast_non_200():
    transport = make_transport({
        ("POST", "/api/services/weather/get_forecasts"): httpx.Response(400, text="Bad Request")
    })
    client = httpx.AsyncClient(transport=transport)
    ha = HomeAssistantClient("http://ha:8123", "tok", client)
    result = await ha.get_weather_forecast("weather.home")
    assert result == []


@pytest.mark.asyncio
async def test_ha_get_weather_forecast_exception():
    def handler(request):
        raise httpx.ConnectError("refused")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ha = HomeAssistantClient("http://ha:8123", "tok", client)
    result = await ha.get_weather_forecast("weather.home")
    assert result == []


@pytest.mark.asyncio
async def test_ha_get_sensor_data_timeout_retries():
    """httpx.TimeoutException → retries, then returns error."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        raise TimeoutError("timed out")

    with patch("asyncio.sleep"):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        ha = HomeAssistantClient("http://ha:8123", "tok", client)
        result = await ha.get_sensor_data("sensor.temp")

    assert "error" in result
    assert call_count == 3


@pytest.mark.asyncio
async def test_ha_get_sensor_states_parallel(ha_sensor_response):
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json=ha_sensor_response)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    ha = HomeAssistantClient("http://ha:8123", "tok", client)
    result = await ha.get_sensor_states(["sensor.a", "sensor.b"])
    assert len(result) == 2
    assert call_count == 2


# ── InfluxDBClient ─────────────────────────────────────────────────────────────

FLUX_CSV_VALID = (
    "#group,false,false,false,false\n"
    "#datatype,string,long,dateTime:RFC3339,double\n"
    "#default,_result,,,\n"
    ",result,table,_time,_value\n"
    ",_result,0,2026-03-15T10:00:00Z,22.5\n"
)

FLUX_CSV_NO_VALUE_COL = (
    "#group,false\n"
    "#datatype,string\n"
    "#default,_result\n"
    ",result\n"
    ",_result\n"
)

FLUX_CSV_NON_NUMERIC = (
    "#group,false\n"
    "#datatype,string,string\n"
    "#default,_result,\n"
    ",result,_value\n"
    ",_result,N/A\n"
)


def _make_influx(http_client=None):
    return InfluxDBClient(
        "http://db:8086", "tok", "home", "org",
        http_client or MagicMock()
    )


def test_parse_flux_csv_valid():
    db = _make_influx()
    assert db._parse_flux_csv(FLUX_CSV_VALID) == 22.5


def test_parse_flux_csv_no_value_column():
    db = _make_influx()
    assert db._parse_flux_csv(FLUX_CSV_NO_VALUE_COL) is None


def test_parse_flux_csv_non_numeric():
    db = _make_influx()
    assert db._parse_flux_csv(FLUX_CSV_NON_NUMERIC) is None


def test_parse_flux_csv_empty():
    db = _make_influx()
    assert db._parse_flux_csv("") is None


@pytest.mark.asyncio
async def test_influx_execute_flux_query_success():
    transport = make_transport({
        ("POST", "/api/v2/query"): httpx.Response(200, text=FLUX_CSV_VALID)
    })
    client = httpx.AsyncClient(transport=transport)
    db = _make_influx(client)
    result = await db._execute_flux_query("from(bucket: \"home\") |> range(start: -1h)")
    assert "_value" in result


@pytest.mark.asyncio
async def test_influx_execute_flux_query_4xx():
    transport = make_transport({
        ("POST", "/api/v2/query"): httpx.Response(400, text="Bad Request")
    })
    client = httpx.AsyncClient(transport=transport)
    db = _make_influx(client)
    result = await db._execute_flux_query("invalid flux")
    assert result.startswith("error:")


@pytest.mark.asyncio
async def test_influx_execute_flux_query_5xx_retries():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, text="Service Unavailable")

    with patch("asyncio.sleep"):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        db = _make_influx(client)
        result = await db._execute_flux_query("flux")

    assert result.startswith("error:")
    assert call_count == 3


@pytest.mark.asyncio
async def test_influx_query_temperature_avg_success():
    transport = make_transport({
        ("POST", "/api/v2/query"): httpx.Response(200, text=FLUX_CSV_VALID)
    })
    client = httpx.AsyncClient(transport=transport)
    db = _make_influx(client)
    result = await db.query_temperature_avg("1h")
    assert result == 22.5


@pytest.mark.asyncio
async def test_influx_query_temperature_avg_error():
    transport = make_transport({
        ("POST", "/api/v2/query"): httpx.Response(400, text="Bad Request")
    })
    client = httpx.AsyncClient(transport=transport)
    db = _make_influx(client)
    result = await db.query_temperature_avg("1h")
    assert result == -999.0


@pytest.mark.asyncio
async def test_influx_query_temperature_avg_no_value():
    transport = make_transport({
        ("POST", "/api/v2/query"): httpx.Response(200, text=FLUX_CSV_NO_VALUE_COL)
    })
    client = httpx.AsyncClient(transport=transport)
    db = _make_influx(client)
    result = await db.query_temperature_avg("1h")
    assert result == -999.0


@pytest.mark.asyncio
async def test_influx_query_humidity_avg_success():
    transport = make_transport({
        ("POST", "/api/v2/query"): httpx.Response(200, text=FLUX_CSV_VALID)
    })
    client = httpx.AsyncClient(transport=transport)
    db = _make_influx(client)
    result = await db.query_humidity_avg("1h")
    assert result == 22.5


@pytest.mark.asyncio
async def test_influx_query_humidity_avg_error():
    transport = make_transport({
        ("POST", "/api/v2/query"): httpx.Response(503, text="err")
    })

    with patch("asyncio.sleep"):
        client = httpx.AsyncClient(transport=transport)
        db = _make_influx(client)
        result = await db.query_humidity_avg("1h")

    assert result == -999.0


@pytest.mark.asyncio
async def test_influx_execute_flux_query_timeout_retries():
    """TimeoutError → retries 3 times."""
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        raise TimeoutError("timed out")

    with patch("asyncio.sleep"):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        db = _make_influx(client)
        result = await db._execute_flux_query("flux")

    assert result.startswith("error:")
    assert call_count == 3


@pytest.mark.asyncio
async def test_influx_execute_flux_query_exception_retries():
    call_count = 0

    def handler(request):
        nonlocal call_count
        call_count += 1
        raise httpx.ConnectError("refused")

    with patch("asyncio.sleep"):
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        db = _make_influx(client)
        result = await db._execute_flux_query("flux")

    assert result.startswith("error:")
    assert call_count == 3


# ── GoogleCalendarClient ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gcal_get_access_token_no_service_account():
    client = httpx.AsyncClient()
    gcal = GoogleCalendarClient({}, client)
    token = await gcal._get_access_token()
    assert token is None


@pytest.mark.asyncio
async def test_gcal_get_access_token_exception():
    with patch("src.fetchers.google_calendar.Credentials") as mock_creds:
        mock_creds.from_service_account_info.side_effect = Exception("auth error")
        client = httpx.AsyncClient()
        gcal = GoogleCalendarClient({"type": "service_account"}, client)
        token = await gcal._get_access_token()
        assert token is None


@pytest.mark.asyncio
async def test_gcal_get_upcoming_events_no_token():
    client = httpx.AsyncClient()
    gcal = GoogleCalendarClient({}, client)  # no service account → no token
    events = await gcal.get_upcoming_events()
    assert events == []


@pytest.mark.asyncio
async def test_gcal_get_upcoming_events_success(google_calendar_events, monkeypatch):
    transport = make_transport({
        ("GET", "googleapis.com/calendar/v3"): httpx.Response(200, json=google_calendar_events)
    })
    http_client = httpx.AsyncClient(transport=transport)
    gcal = GoogleCalendarClient({"type": "service_account"}, http_client)

    async def fake_token(self):
        return "fake-token"

    monkeypatch.setattr(GoogleCalendarClient, "_get_access_token", fake_token)
    events = await gcal.get_upcoming_events()
    assert len(events) == 3
    assert events[0]["summary"] == "Standup"


@pytest.mark.asyncio
async def test_gcal_get_upcoming_events_all_day(monkeypatch):
    all_day_response = {
        "items": [
            {
                "summary": "Conference",
                "start": {"date": "2026-03-20"},
                "end": {"date": "2026-03-21"},
            }
        ]
    }
    transport = make_transport({
        ("GET", "googleapis.com/calendar/v3"): httpx.Response(200, json=all_day_response)
    })
    http_client = httpx.AsyncClient(transport=transport)
    gcal = GoogleCalendarClient({"type": "service_account"}, http_client)

    async def fake_token(self):
        return "fake-token"

    monkeypatch.setattr(GoogleCalendarClient, "_get_access_token", fake_token)
    events = await gcal.get_upcoming_events()
    assert len(events) == 1
    assert events[0]["start"] == "2026-03-20"


@pytest.mark.asyncio
async def test_gcal_get_upcoming_events_non_200(monkeypatch):
    transport = make_transport({
        ("GET", "googleapis.com/calendar/v3"): httpx.Response(403, text="Forbidden")
    })
    http_client = httpx.AsyncClient(transport=transport)
    gcal = GoogleCalendarClient({"type": "service_account"}, http_client)

    async def fake_token(self):
        return "fake-token"

    monkeypatch.setattr(GoogleCalendarClient, "_get_access_token", fake_token)
    events = await gcal.get_upcoming_events()
    assert events == []


@pytest.mark.asyncio
async def test_gcal_get_upcoming_events_exception(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("refused")

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    gcal = GoogleCalendarClient({"type": "service_account"}, http_client)

    async def fake_token(self):
        return "fake-token"

    monkeypatch.setattr(GoogleCalendarClient, "_get_access_token", fake_token)
    events = await gcal.get_upcoming_events()
    assert events == []
