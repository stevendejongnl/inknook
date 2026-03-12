"""Integration test fixtures with testcontainers."""

import os
import time
from collections.abc import Generator

import httpx
import pytest
from testcontainers.compose import DockerCompose

# Use testcontainers only if Docker is available
SKIP_TESTCONTAINERS = os.getenv("SKIP_TESTCONTAINERS", "").lower() in ("1", "true")


@pytest.fixture(scope="session")
def docker_compose_file() -> str:
    """Return path to docker-compose file for integration tests."""
    return os.path.join(os.path.dirname(__file__), "docker-compose.yml")


@pytest.fixture(scope="session")
def compose(docker_compose_file: str) -> Generator:
    """Start Docker Compose services for integration tests."""
    if SKIP_TESTCONTAINERS:
        pytest.skip("Docker/testcontainers not available")

    with DockerCompose(
        filepath=os.path.dirname(docker_compose_file),
        compose_file_name=os.path.basename(docker_compose_file),
        pull=True,
        wait_for_services=True,
        timeout=120,
    ) as compose:
        # Wait for services to be ready
        time.sleep(5)
        yield compose


@pytest.fixture(scope="session")
def influxdb_url(compose: DockerCompose) -> str:
    """Get InfluxDB URL from compose services."""
    if SKIP_TESTCONTAINERS:
        pytest.skip("Docker/testcontainers not available")
    return "http://localhost:8086"


@pytest.fixture(scope="session")
def influxdb_token(compose: DockerCompose) -> str:
    """Get InfluxDB token from compose services."""
    if SKIP_TESTCONTAINERS:
        pytest.skip("Docker/testcontainers not available")
    return "testtoken123456789"


@pytest.fixture(scope="session")
def home_assistant_url(compose: DockerCompose) -> str:
    """Get Home Assistant URL from compose services."""
    if SKIP_TESTCONTAINERS:
        pytest.skip("Docker/testcontainers not available")
    return "http://localhost:8123"


@pytest.fixture(scope="session")
def home_assistant_token(compose: DockerCompose) -> str:
    """Get Home Assistant token from compose services."""
    if SKIP_TESTCONTAINERS:
        pytest.skip("Docker/testcontainers not available")
    return "test-ha-token"


@pytest.fixture
async def http_client() -> httpx.AsyncClient:
    """Create async HTTP client for integration tests."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client
