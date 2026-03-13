"""Home Assistant REST API client."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HomeAssistantClient:
    """Async client for Home Assistant REST API."""

    def __init__(self, url: str, token: str, http_client: httpx.AsyncClient) -> None:
        """
        Initialize Home Assistant client.

        Args:
            url: Home Assistant base URL (e.g., http://home-assistant:8123)
            token: Long-lived access token
            http_client: httpx AsyncClient for making requests
        """
        self.url = url.rstrip("/")
        self.token = token
        self.http_client = http_client

    def _headers(self) -> dict[str, str]:
        """Get HTTP headers with authentication."""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    async def get_sensor_data(self, entity_id: str) -> dict[str, Any]:
        """
        Fetch sensor state from Home Assistant.

        Args:
            entity_id: Entity ID to query (e.g., 'weather.home', 'sensor.temperature')

        Returns:
            Dict with state and attributes, or {"error": "..."} on failure

        Implementation:
        - GET /api/states/{entity_id}
        - Retry 3x with exponential backoff: 1s, 2s, 4s
        - On any error (timeout, 5xx, etc.), return {"error": "<message>"}
        - Timeout: 10 seconds per request
        """
        import asyncio

        url = f"{self.url}/api/states/{entity_id}"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = await self.http_client.get(url, headers=self._headers())
                if response.status_code == 200:
                    logger.info(f"HA: Successfully fetched {entity_id}")
                    return response.json()
                elif response.status_code >= 500:
                    # 5xx error, retry
                    logger.warning(
                        f"HA: Got {response.status_code} for {entity_id}, retrying..."
                    )
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    # 4xx error, don't retry
                    return {"error": f"HTTP {response.status_code}: {response.text}"}
            except TimeoutError:
                logger.warning(f"HA: Timeout fetching {entity_id}, retrying...")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
            except Exception as e:
                logger.error(f"HA: Exception fetching {entity_id}: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue

        return {"error": f"Failed to fetch {entity_id} after {max_retries} attempts"}

    async def get_weather_forecast(
        self, entity_id: str = "weather.home"
    ) -> list[dict[str, Any]]:
        """
        Fetch 24h hourly forecast via HA service action API.

        HA 2024.4+ requires ?return_response=true and wraps the result under
        a "service_response" key. Older versions return the dict directly.

        Returns up to 24 hourly forecast dicts, or [] on failure.
        """
        url = f"{self.url}/api/services/weather/get_forecasts"
        payload = {"entity_id": entity_id, "type": "hourly"}
        try:
            response = await self.http_client.post(
                url,
                headers=self._headers(),
                json=payload,
                params={"return_response": "true"},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                # HA 2024.4+ wraps result in {"service_response": {...}}
                if isinstance(data, dict) and "service_response" in data:
                    data = data["service_response"]
                forecasts = (
                    data.get(entity_id, {}).get("forecast", [])
                    or data.get("weather.home", {}).get("forecast", [])
                ) if isinstance(data, dict) else []
                logger.info(f"HA forecast: {len(forecasts)} hourly entries")
                return forecasts[:24]
            logger.warning(f"HA forecast: HTTP {response.status_code} — {response.text[:200]}")
            return []
        except Exception as e:
            logger.warning(f"HA forecast fetch failed: {e}")
            return []

    async def get_sensor_states(
        self, entity_ids: list[str]
    ) -> list[dict[str, Any]]:
        """Fetch multiple entity states in parallel. Returns one result per entity_id."""
        import asyncio

        tasks = [self.get_sensor_data(eid) for eid in entity_ids]
        return list(await asyncio.gather(*tasks))
