"""Configuration management with environment variables."""

from base64 import b64decode
from json import loads

from pydantic_settings import BaseSettings


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
