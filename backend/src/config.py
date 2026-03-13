"""Configuration management with environment variables."""

import logging
from base64 import b64decode
from json import loads
from pathlib import Path

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class SensorConfig(BaseModel):
    """A single configurable sensor entry from sensors.yaml."""

    entity_id: str
    label: str
    unit: str | None = None  # If None, uses HA's unit_of_measurement


class DepartureConfig(BaseModel):
    """A public transport departure sensor entry from sensors.yaml."""

    entity_id: str
    short_direction: str | None = None  # Optional abbreviation for the display
    max_departures: int = 4  # How many upcoming times to show


def _load_yaml() -> dict:
    path = Path(__file__).parent.parent / "sensors.yaml"
    if not path.exists():
        logger.warning(f"sensors.yaml not found at {path}")
        return {}
    try:
        with open(path) as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load sensors.yaml: {e}")
        return {}


def load_sensor_configs() -> list[SensorConfig]:
    """Load sensor panel configuration from sensors.yaml."""
    data = _load_yaml()
    try:
        return [SensorConfig(**s) for s in data.get("sensors", [])]
    except Exception as e:
        logger.error(f"Invalid sensor config: {e}")
        return []


def load_departure_configs() -> list[DepartureConfig]:
    """Load departure sensor configuration from sensors.yaml."""
    data = _load_yaml()
    try:
        return [DepartureConfig(**d) for d in data.get("departures", [])]
    except Exception as e:
        logger.error(f"Invalid departure config: {e}")
        return []


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Home Assistant
    ha_url: str
    ha_token: str

    # InfluxDB
    influxdb_url: str
    influxdb_token: str
    influxdb_bucket: str = "home"
    influxdb_org: str = "my-org"

    # Google Calendar (base64-encoded service account JSON)
    google_service_account_json_b64: str = ""
    google_calendar_id: str = "primary"

    # Display timezone (IANA name, e.g. Europe/Amsterdam)
    display_timezone: str = "Europe/Amsterdam"

    # Invert display output (true for e-paper drivers that read 0=white, 1=black)
    display_invert: bool = True

    # Cache TTLs (seconds)
    cache_ttl_ha: int = 300
    cache_ttl_influxdb: int = 300
    cache_ttl_calendar: int = 3600

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def google_service_account_json(self) -> dict:
        """Decode base64-encoded Google service account JSON."""
        if not self.google_service_account_json_b64:
            return {}
        try:
            decoded = b64decode(self.google_service_account_json_b64).decode("utf-8")
            return loads(decoded)
        except Exception as e:
            raise ValueError(f"Failed to decode Google service account JSON: {e}")


settings = Settings()
