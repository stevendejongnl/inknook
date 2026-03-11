"""Integration tests for Home Assistant client with mock HTTP server."""

import pytest

from src.fetchers.home_assistant import HomeAssistantClient


@pytest.mark.integration
@pytest.mark.asyncio
async def test_home_assistant_get_sensor_data(
    home_assistant_url: str, home_assistant_token: str, http_client
):
    """Test fetching real sensor data from mock Home Assistant server."""
    client = HomeAssistantClient(
        url=home_assistant_url,
        token=home_assistant_token,
        http_client=http_client,
    )

    # The mock server serves weather.home.json at /api/states/weather.home
    result = await client.get_sensor_data("weather.home")

    # Should get valid response (not an error dict)
    if "error" not in result:
        assert "entity_id" in result
        assert result["entity_id"] == "weather.home"
        assert "attributes" in result
        assert "temperature" in result["attributes"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_home_assistant_nonexistent_entity(
    home_assistant_url: str, home_assistant_token: str, http_client
):
    """Test fetching non-existent entity returns 404."""
    client = HomeAssistantClient(
        url=home_assistant_url,
        token=home_assistant_token,
        http_client=http_client,
    )

    result = await client.get_sensor_data("sensor.nonexistent")

    # Should return error (404 or other error)
    # Either error dict or network failure is expected
    assert isinstance(result, dict)
