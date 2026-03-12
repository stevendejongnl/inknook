"""InfluxDB async client for Flux queries."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class InfluxDBClient:
    """Async client for InfluxDB 2.x Flux API."""

    def __init__(
        self,
        url: str,
        token: str,
        bucket: str,
        org: str,
        http_client: httpx.AsyncClient,
    ) -> None:
        """
        Initialize InfluxDB client.

        Args:
            url: InfluxDB base URL (e.g., http://influxdb:8086)
            token: API token with read permissions
            bucket: Default bucket for queries
            org: Organization ID or name
            http_client: httpx AsyncClient for requests
        """
        self.url = url.rstrip("/")
        self.token = token
        self.bucket = bucket
        self.org = org
        self.http_client = http_client

    def _headers(self) -> dict[str, str]:
        """Get HTTP headers with authentication."""
        return {
            "Authorization": f"Token {self.token}",
            "Content-Type": "application/vnd.flux",
            "Accept": "application/json",
        }

    async def query_temperature_avg(self, duration: str = "1h") -> float:
        """
        Query average temperature over duration.

        Args:
            duration: Time range (e.g., '1h', '24h')

        Returns:
            Average temperature as float, or -999.0 on error

        Implementation:
        - Build Flux query: |> range(start: -{duration}) |> mean()
        - POST to /api/v2/query
        - Parse JSON response table data
        - Return mean value or -999.0 on error
        """
        flux = f"""
        from(bucket: "{self.bucket}")
        |> range(start: -{duration})
        |> filter(fn: (r) => r._measurement == "temperature")
        |> mean()
        """
        result = await self._execute_flux_query(flux)

        if "error" in result:
            logger.error(f"InfluxDB: Temperature query failed: {result['error']}")
            return -999.0

        try:
            # Extract mean value from Flux response
            if "tables" not in result or not result["tables"]:
                return -999.0
            table = result["tables"][0]
            if "data" not in table or not table["data"]:
                return -999.0
            # Value is typically in column index 3 (after time, field, measurement)
            value = table["data"][0][3]
            logger.info(f"InfluxDB: Temperature avg = {value}")
            return float(value)
        except (IndexError, KeyError, TypeError, ValueError) as e:
            logger.error(f"InfluxDB: Failed to parse temperature response: {e}")
            return -999.0

    async def query_humidity_avg(self, duration: str = "1h") -> float:
        """
        Query average humidity over duration.

        Args:
            duration: Time range (e.g., '1h', '24h')

        Returns:
            Average humidity as float, or -999.0 on error
        """
        flux = f"""
        from(bucket: "{self.bucket}")
        |> range(start: -{duration})
        |> filter(fn: (r) => r._measurement == "humidity")
        |> mean()
        """
        result = await self._execute_flux_query(flux)

        if "error" in result:
            logger.error(f"InfluxDB: Humidity query failed: {result['error']}")
            return -999.0

        try:
            if "tables" not in result or not result["tables"]:
                return -999.0
            table = result["tables"][0]
            if "data" not in table or not table["data"]:
                return -999.0
            value = table["data"][0][3]
            logger.info(f"InfluxDB: Humidity avg = {value}")
            return float(value)
        except (IndexError, KeyError, TypeError, ValueError) as e:
            logger.error(f"InfluxDB: Failed to parse humidity response: {e}")
            return -999.0

    async def _execute_flux_query(self, flux: str) -> dict[str, Any]:
        """
        Execute Flux query and return parsed JSON.

        Args:
            flux: Flux query string

        Returns:
            Parsed JSON response dict, or {"error": "..."} on failure
        """
        import asyncio

        url = f"{self.url}/api/v2/query"
        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = await self.http_client.post(
                    url,
                    headers=self._headers(),
                    content=flux,
                )
                if response.status_code == 200:
                    logger.info("InfluxDB: Query succeeded")
                    return response.json()
                elif response.status_code >= 500:
                    logger.warning(
                        f"InfluxDB: Got {response.status_code}, retrying..."
                    )
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                    continue
                else:
                    return {"error": f"HTTP {response.status_code}"}
            except TimeoutError:
                logger.warning("InfluxDB: Timeout, retrying...")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue
            except Exception as e:
                logger.error(f"InfluxDB: Exception: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                continue

        return {"error": f"Failed after {max_retries} attempts"}
