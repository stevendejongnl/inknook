"""InfluxDB async client for Flux queries."""

import asyncio
import csv
import io
import logging

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
            "Accept": "text/csv",
        }

    def _parse_flux_csv(self, text: str) -> float | None:
        """Extract _value from annotated CSV Flux response."""
        reader = csv.reader(io.StringIO(text))
        header: list[str] | None = None
        value_idx: int | None = None
        for row in reader:
            if not row or row[0].startswith("#"):
                continue
            if header is None:
                header = row
                try:
                    value_idx = header.index("_value")
                except ValueError:
                    return None
                continue
            if value_idx is not None and len(row) > value_idx:
                try:
                    return float(row[value_idx])
                except (ValueError, TypeError):
                    return None
        return None

    async def query_temperature_avg(self, duration: str = "1h") -> float:
        """
        Query average temperature over duration.

        Args:
            duration: Time range (e.g., '1h', '24h')

        Returns:
            Average temperature as float, or -999.0 on error
        """
        flux = f"""
        from(bucket: "{self.bucket}")
        |> range(start: -{duration})
        |> filter(fn: (r) => r._measurement == "\u00b0C" and r._field == "value")
        |> filter(fn: (r) => r.entity_id == "average_house_temperature")
        |> mean()
        """
        csv_text = await self._execute_flux_query(flux)

        if csv_text.startswith("error:"):
            logger.error(f"InfluxDB: Temperature query failed: {csv_text}")
            return -999.0

        value = self._parse_flux_csv(csv_text)
        if value is None:
            return -999.0
        logger.info(f"InfluxDB: Temperature avg = {value}")
        return value

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
        |> filter(fn: (r) => r._measurement == "%" and r._field == "value")
        |> filter(fn: (r) => r.entity_id == "living_room_back_humidity")
        |> mean()
        """
        csv_text = await self._execute_flux_query(flux)

        if csv_text.startswith("error:"):
            logger.error(f"InfluxDB: Humidity query failed: {csv_text}")
            return -999.0

        value = self._parse_flux_csv(csv_text)
        if value is None:
            return -999.0
        logger.info(f"InfluxDB: Humidity avg = {value}")
        return value

    async def _execute_flux_query(self, flux: str) -> str:
        """
        Execute Flux query and return CSV text.

        Args:
            flux: Flux query string

        Returns:
            Annotated CSV response text, or "error: ..." on failure
        """
        url = f"{self.url}/api/v2/query?org={self.org}"
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
                    return response.text
                elif response.status_code >= 500:
                    logger.warning(
                        f"InfluxDB: Got {response.status_code}, retrying..."
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                    continue
                else:
                    return f"error: HTTP {response.status_code}"
            except TimeoutError:
                logger.warning("InfluxDB: Timeout, retrying...")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                continue
            except Exception as e:
                logger.error(f"InfluxDB: Exception: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)
                continue

        return f"error: Failed after {max_retries} attempts"
