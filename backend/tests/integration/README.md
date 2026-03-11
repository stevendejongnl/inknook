# Integration Tests with Testcontainers

This directory contains **integration tests** that use **testcontainers** to spin up real Docker services instead of mocks.

## Why Testcontainers?

- **Real Services**: Test against actual InfluxDB, Home Assistant, etc. (not mocks)
- **End-to-End Validation**: Verify your code works with real APIs
- **Confidence**: Catch issues that mocks might miss (e.g., API changes, query syntax)
- **Development**: Great for local development and debugging

## What's Tested

### InfluxDB Integration (`test_influxdb_real.py`)

- **Connection**: Can connect to real InfluxDB instance
- **Flux Queries**: Execute actual Flux queries
- **Temperature/Humidity**: Test aggregation queries with real database

### Home Assistant Integration (`test_home_assistant_real.py`)

- **REST API**: Fetch sensor data from mock HTTP server
- **Error Handling**: Handle 404s and other HTTP errors gracefully
- **Data Parsing**: Verify response format matches expectations

## Running Integration Tests

### Prerequisites

- Docker must be installed and running
- Compose file available: `docker-compose.yml`

### Run All Integration Tests

```bash
# Using pytest directly
uv run pytest tests/integration -v -m integration

# Using Makefile shortcut
make test-integration

# Run all tests (unit + integration)
make test-all
```

### Run Specific Integration Test

```bash
# InfluxDB tests only
uv run pytest tests/integration/test_influxdb_real.py -v -m integration

# Home Assistant tests only
uv run pytest tests/integration/test_home_assistant_real.py -v -m integration
```

### Skip Integration Tests

Integration tests are **automatically skipped** if:
- Docker is not available
- `SKIP_TESTCONTAINERS=1` environment variable is set

```bash
# Skip integration tests (unit tests only)
SKIP_TESTCONTAINERS=1 make test

# Or using pytest marker
pytest -v -m "not integration"
```

## Docker Compose Services

The `docker-compose.yml` starts:

1. **InfluxDB 2.7**
   - Port: `8086`
   - Token: `testtoken123456789`
   - Bucket: `home`
   - Org: `my-org`

2. **Home Assistant Mock Server**
   - Port: `8123`
   - Serves mock API responses from `ha-mock-data/` directory
   - Example: `/api/states/weather.home.json`

## Test Structure

```
tests/integration/
├── conftest.py                 # Pytest fixtures + testcontainers setup
├── docker-compose.yml          # Service definitions
├── ha-mock-data/               # Mock HA API responses
│   └── api/states/
│       └── weather.home.json   # Sample response
├── test_influxdb_real.py       # InfluxDB client tests
├── test_home_assistant_real.py # HA client tests
└── README.md                   # This file
```

## Environment Variables

### Skip Integration Tests

```bash
SKIP_TESTCONTAINERS=1 pytest
```

### Custom Service Ports

Edit `docker-compose.yml` to change port mappings:

```yaml
services:
  influxdb:
    ports:
      - "8086:8086"  # Change left number for host port
```

## Troubleshooting

### "Docker daemon not running"

```bash
# Start Docker
docker daemon

# Or on macOS with Docker Desktop:
# Open Docker.app from Applications
```

### "Port already in use"

```bash
# Find process using port 8086
lsof -i :8086

# Kill process (get PID from above)
kill -9 <PID>
```

### "Compose file not found"

Ensure you're running pytest from the project root:

```bash
cd /path/to/inknook-backend
uv run pytest tests/integration -v -m integration
```

### Services don't start in time

Edit `conftest.py` to increase timeout:

```python
with DockerCompose(
    ...
    timeout=300,  # Increase from 120
)
```

## Adding New Integration Tests

1. Create new test file in `tests/integration/test_*.py`
2. Add `@pytest.mark.integration` decorator
3. Use `compose`, `influxdb_url`, `http_client` fixtures from `conftest.py`
4. Define service dependencies in `docker-compose.yml`

Example:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_my_feature(influxdb_url: str, http_client):
    """Test something with real InfluxDB."""
    # Your test here
    pass
```

## Performance Considerations

- **Startup Time**: First run takes 30-60 seconds (pulls images, starts containers)
- **Caching**: Images are cached, subsequent runs are faster
- **Isolation**: Each test session has fresh containers
- **Resource Usage**: Keep Docker memory settings adequate

## CI/CD Integration

Integration tests can run in CI/CD pipelines:

```yaml
# GitHub Actions example
- name: Run integration tests
  run: |
    uv sync --all-extras
    uv run pytest tests/integration -v -m integration
```

Requires Docker-in-Docker or similar setup.

## References

- [Testcontainers Python](https://testcontainers-python.readthedocs.io/)
- [Docker Compose](https://docs.docker.com/compose/)
- [InfluxDB Docker](https://hub.docker.com/_/influxdb)
