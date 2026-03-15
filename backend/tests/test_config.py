"""Tests for configuration management."""

import base64
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.config import (
    DepartureConfig,
    SensorConfig,
    Settings,
    _load_yaml,
    load_departure_configs,
    load_sensor_configs,
)


# ── _load_yaml ─────────────────────────────────────────────────────────────────

def test_load_yaml_missing(tmp_path):
    """When sensors.yaml doesn't exist, returns {}."""
    nonexistent = tmp_path / "sensors.yaml"
    with patch("src.config.Path") as mock_path_cls:
        # Make Path(__file__).parent.parent / "sensors.yaml" return nonexistent
        instance = mock_path_cls.return_value
        instance.parent.parent.__truediv__.return_value = nonexistent
        result = _load_yaml()
    assert result == {}


def test_load_yaml_valid(tmp_path):
    """When sensors.yaml exists and is valid, returns parsed dict."""
    data = {
        "sensors": [
            {"entity_id": "sensor.temp", "label": "Temp"}
        ]
    }
    yaml_file = tmp_path / "sensors.yaml"
    yaml_file.write_text(yaml.dump(data))

    with patch("src.config.Path") as mock_path_cls:
        instance = mock_path_cls.return_value
        instance.parent.parent.__truediv__.return_value = yaml_file
        result = _load_yaml()

    assert "sensors" in result
    assert result["sensors"][0]["entity_id"] == "sensor.temp"


def test_load_yaml_parse_error(tmp_path):
    """When sensors.yaml has invalid YAML, returns {}."""
    bad_yaml = tmp_path / "sensors.yaml"
    bad_yaml.write_text("key: [unclosed bracket")

    with patch("src.config.Path") as mock_path_cls:
        instance = mock_path_cls.return_value
        instance.parent.parent.__truediv__.return_value = bad_yaml
        result = _load_yaml()

    assert result == {}


def test_load_yaml_empty_file(tmp_path):
    """When sensors.yaml is empty, returns {}."""
    empty = tmp_path / "sensors.yaml"
    empty.write_text("")

    with patch("src.config.Path") as mock_path_cls:
        instance = mock_path_cls.return_value
        instance.parent.parent.__truediv__.return_value = empty
        result = _load_yaml()

    assert result == {}


# ── load_sensor_configs ────────────────────────────────────────────────────────

def test_load_sensor_configs_valid():
    data = {
        "sensors": [
            {"entity_id": "sensor.temp", "label": "Temperature"},
            {"entity_id": "sensor.hum", "label": "Humidity", "unit": "%"},
        ]
    }
    with patch("src.config._load_yaml", return_value=data):
        result = load_sensor_configs()
    assert len(result) == 2
    assert isinstance(result[0], SensorConfig)
    assert result[0].entity_id == "sensor.temp"
    assert result[1].unit == "%"


def test_load_sensor_configs_empty():
    with patch("src.config._load_yaml", return_value={}):
        result = load_sensor_configs()
    assert result == []


def test_load_sensor_configs_invalid():
    """Malformed sensor entry (missing required fields) → empty list."""
    data = {"sensors": [{"bad_field": "value"}]}
    with patch("src.config._load_yaml", return_value=data):
        result = load_sensor_configs()
    assert result == []


# ── load_departure_configs ─────────────────────────────────────────────────────

def test_load_departure_configs_valid():
    data = {
        "departures": [
            {"entity_id": "sensor.bus_340", "short_direction": "CS", "max_departures": 3},
        ]
    }
    with patch("src.config._load_yaml", return_value=data):
        result = load_departure_configs()
    assert len(result) == 1
    assert isinstance(result[0], DepartureConfig)
    assert result[0].short_direction == "CS"
    assert result[0].max_departures == 3


def test_load_departure_configs_defaults():
    data = {"departures": [{"entity_id": "sensor.bus"}]}
    with patch("src.config._load_yaml", return_value=data):
        result = load_departure_configs()
    assert result[0].max_departures == 4  # default
    assert result[0].short_direction is None


def test_load_departure_configs_empty():
    with patch("src.config._load_yaml", return_value={}):
        result = load_departure_configs()
    assert result == []


def test_load_departure_configs_invalid():
    data = {"departures": [{"bad_field": "value"}]}
    with patch("src.config._load_yaml", return_value=data):
        result = load_departure_configs()
    assert result == []


# ── Settings.google_service_account_json ──────────────────────────────────────

def test_settings_google_json_empty(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://ha:8123")
    monkeypatch.setenv("HA_TOKEN", "tok")
    monkeypatch.setenv("INFLUXDB_URL", "http://db:8086")
    monkeypatch.setenv("INFLUXDB_TOKEN", "tok")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "")
    s = Settings()
    assert s.google_service_account_json == {}


def test_settings_google_json_valid(monkeypatch):
    payload = {"type": "service_account", "project_id": "my-proj"}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    monkeypatch.setenv("HA_URL", "http://ha:8123")
    monkeypatch.setenv("HA_TOKEN", "tok")
    monkeypatch.setenv("INFLUXDB_URL", "http://db:8086")
    monkeypatch.setenv("INFLUXDB_TOKEN", "tok")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", encoded)
    s = Settings()
    assert s.google_service_account_json == payload


def test_settings_google_json_invalid_b64(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://ha:8123")
    monkeypatch.setenv("HA_TOKEN", "tok")
    monkeypatch.setenv("INFLUXDB_URL", "http://db:8086")
    monkeypatch.setenv("INFLUXDB_TOKEN", "tok")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON_B64", "!!!notbase64!!!")
    s = Settings()
    with pytest.raises(ValueError):
        _ = s.google_service_account_json
