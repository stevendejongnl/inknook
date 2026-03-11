"""Home Assistant REST API client."""

import logging
from typing import Any, Optional

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
            except asyncio.TimeoutError:
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
