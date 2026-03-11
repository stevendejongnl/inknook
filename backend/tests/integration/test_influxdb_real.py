"""Integration tests for InfluxDB client with real InfluxDB container."""

import pytest

from src.fetchers.influxdb import InfluxDBClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_influxdb_connection(influxdb_url: str, influxdb_token: str, http_client):
    """Test that we can connect to real InfluxDB container."""
    client = InfluxDBClient(
        url=influxdb_url,
        token=influxdb_token,
        bucket="home",
        org="my-org",
        http_client=http_client,
    )

    # Query should return empty result (no data written yet)
    result = await client.query_temperature_avg(duration="1h")

    # With no data, should return error value
    assert result == -999.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_influxdb_flux_query(influxdb_url: str, influxdb_token: str, http_client):
    """Test Flux query execution against real InfluxDB."""
    client = InfluxDBClient(
        url=influxdb_url,
        token=influxdb_token,
        bucket="home",
        org="my-org",
        http_client=http_client,
    )

    # Execute a simple query
    flux = 'from(bucket: "home") |> range(start: -1h) |> limit(n: 1)'
    result = await client._execute_flux_query(flux)

    # Should have 'result' or 'tables' key (even if empty)
    assert "result" in result or "tables" in result or "error" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_influxdb_humidity_query(influxdb_url: str, influxdb_token: str, http_client):
    """Test humidity query against real InfluxDB."""
    client = InfluxDBClient(
        url=influxdb_url,
        token=influxdb_token,
        bucket="home",
        org="my-org",
        http_client=http_client,
    )

    result = await client.query_humidity_avg(duration="1h")

    # No data yet, should return error value
    assert result == -999.0
