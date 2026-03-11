# inknook-backend

FastAPI backend rendering an 800×480 B/W BMP dashboard for a **DFRobot FireBeetle 2 ESP32-E** with **Waveshare 7.5" V2 e-paper display** running **ESPHome firmware**.

## Architecture

**Stateless image rendering microservice** — No database, no sessions. Pure function: fetch data from external APIs → render PIL Image → return BMP/PNG bytes.

### Data Sources
- **Home Assistant** — Weather (temperature, condition, wind speed)
- **InfluxDB** — Aggregated sensor data (temperature avg, humidity avg)
- **Google Calendar** — Upcoming events (via service account JWT)

### Cache Strategy
- Per-source TTL cache with `asyncio.Lock` to prevent thundering herd
- Independent refresh rates: HA 5min, InfluxDB 5min, Calendar 1hr
- Graceful fallback: returns stale cache if fetch fails

### Rendering
- **800×480 pixels, 1-bit B/W mode**
- **Three panels**: Weather (top-left), Sensors (top-right), Calendar (bottom)
- **Floyd-Steinberg dithering** for grayscale conversion
- **Graceful degradation**: missing data → placeholder text

## Setup

### Local Development

```bash
cd /home/stevendejong/workspace/personal/iot/epaper/backend

# Install dependencies
uv sync

# Copy environment template and fill in credentials
cp .env.example .env
# Edit .env with your API credentials

# Run server
uv run uvicorn src.main:app --reload --port 8080

# Verify health
curl http://localhost:8080/health
# {"status": "ok"}

# View dashboard
curl http://localhost:8080/display.bmp -o dashboard.bmp
open dashboard.bmp
```

### Running Tests

### Unit Tests (No Docker Required)

```bash
# Run all unit tests with coverage (95% required)
uv run pytest --cov=src --cov-fail-under=95

# Run specific test
uv run pytest tests/test_cache.py -v

# Fast tests without coverage check
uv run pytest --cov-fail-under=0
```

### Integration Tests (Requires Docker)

```bash
# Run integration tests with real services
uv run pytest tests/integration -v -m integration

# Or use Makefile shortcut
make test-integration

# Run all tests (unit + integration)
make test-all
```

Integration tests use **testcontainers** to spin up real Docker containers:
- **InfluxDB** — Test Flux queries against real InfluxDB instance
- **Home Assistant mock** — Test REST API calls with mock HTTP server

### Code Quality

```bash
# Lint code (ruff)
uv run ruff check .

# Type checking (mypy)
uv run mypy src/

# Run all quality checks
make check
```

## API Endpoints

### `GET /health`
Simple health check.
```
200 OK: {"status": "ok"}
```

### `GET /display.bmp`
Render and return BMP image (800×480, B/W).
```
200 OK: <binary BMP data>
Content-Type: image/bmp

Query params:
- force_refresh=true  → Invalidate cache, fetch fresh data
```

### `GET /display.png`
Same as above, PNG format instead of BMP.
```
200 OK: <binary PNG data>
Content-Type: image/png
```

### `GET /cache/status`
Debug endpoint showing cache state.
```
200 OK: {
  "ha": {
    "expired": false,
    "last_updated": "2026-03-10T15:30:00",
    "expires_at": "2026-03-10T15:35:00",
    "ttl_remaining_seconds": 123
  },
  "influxdb": { ... },
  "calendar": { ... }
}
```

## Environment Variables

See `.env.example` for full list. Key variables:

```bash
# Home Assistant
HA_URL=http://home-assistant:8123
HA_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...

# InfluxDB
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=xxx
INFLUXDB_BUCKET=home
INFLUXDB_ORG=my-org

# Google Calendar (base64-encoded service account JSON)
GOOGLE_SERVICE_ACCOUNT_JSON_B64=ewogICJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIs...

# Cache TTLs (seconds)
CACHE_TTL_HA=300
CACHE_TTL_INFLUXDB=300
CACHE_TTL_CALENDAR=3600
```

## Implementation Status

### Phase 1: Scaffold ✅
- [x] `pyproject.toml` — Dependencies + tool config
- [x] `src/config.py` — Pydantic settings
- [x] `src/main.py` — FastAPI factory + lifespan
- [x] `src/dependencies.py` — DI wiring
- [x] `src/routers/health.py` — Health endpoint
- [x] `tests/conftest.py` — Test fixtures + mocking

### Phase 2: Fetchers (User Implementation)
- [ ] `src/fetchers/home_assistant.py` — HA REST API client with retry logic
- [ ] `src/fetchers/influxdb.py` — Flux query client
- [ ] `src/fetchers/google_calendar.py` — Calendar API with JWT auth

### Phase 3: Services (User Implementation)
- [ ] `src/services/cache.py` — TTLCache with locking
- [ ] `src/services/renderer.py` — Dashboard image rendering

### Phase 4: Routers (Pending Fetchers)
- [ ] `src/routers/display.py` — Image endpoints
- [ ] `src/routers/cache.py` — Cache status endpoint

### Phase 5: Testing
- [ ] Unit tests for all fetchers, cache, renderer
- [ ] Integration tests for routers
- [ ] 95% coverage

### Phase 6: Infrastructure
- [ ] `Dockerfile` — Multi-stage build
- [ ] `kubernetes.yaml` — K8s deployment
- [ ] `.github/workflows/ci.yml` — Test + build automation

## Key Design Decisions

### 1. Cache Architecture
- **Class-based `TTLCache`** with per-source `asyncio.Lock`
- **Independent TTLs** for each source (HA/InfluxDB: 5min, Calendar: 1hr)
- **No automatic deletion** of expired entries (overwritten on next `set()`)
- **Graceful fallback**: fetch failure returns cached data if available

### 2. Renderer Architecture
- **Single `render_dashboard()` function** — Not composable; one 800×480 output
- **Helper functions** for each panel: `_draw_weather_panel()`, `_draw_sensors_panel()`, `_draw_calendar_panel()`
- **Graceful degradation** — Missing/error data → placeholder text

### 3. External API Retries
- **httpx with exponential backoff** — 1s, 2s, 4s max
- **Timeout: 10 seconds per request**
- **Max 3 attempts** per source
- **Returns error dict on all failures** (not exception)

### 4. Testing Strategy
- **Fixture-based**: Load test data from `tests/fixtures/` JSON files
- **No pixel comparison**: Test dimensions (800×480), mode ('1'), graceful rendering
- **Dependency injection in tests**: Override fetchers/cache with test doubles

### 5. B/W Dithering
- **PIL `Image.convert('1', dither=Image.FLOYDSTEINBERG)`**
- **Produces acceptable grayscale on 1-bit display**
- **Avoids harsh thresholding**

## Deployment

### Docker
```bash
docker build -t inknook-backend:latest .
docker run -p 8080:8000 \
  -e HA_URL=http://home-assistant:8123 \
  -e HA_TOKEN=xxx \
  inknook-backend:latest
```

### Kubernetes
```bash
kubectl apply -f kubernetes.yaml

# Verify
kubectl get pods -n inknook-backend
kubectl logs -n inknook-backend -l app=inknook-backend

# ESPHome fetches from:
curl http://inknook-backend.inknook-backend.svc.cluster.local:8000/display.bmp
```

### ESP32 / ESPHome
Configure ESPHome to fetch BMP every 10 minutes:
```yaml
esphome:
  name: epaper

esp32:
  board: esp32-s3-devkitc-1

display:
  - platform: waveshare_epd
    cs_pin: GPIO46
    dc_pin: GPIO3
    busy_pin: GPIO9
    reset_pin: GPIO1
    model: 7.5in_v2
    update_interval: 600s
    # Fetch BMP from backend
    lambda: |-
      http_client.get("http://inknook-backend:8000/display.bmp");
      // Draw image on display
```

## Next Steps

1. **Implement Phase 2 fetchers** — Home Assistant, InfluxDB, Google Calendar clients
2. **Implement Phase 3 services** — TTLCache and renderer logic
3. **Add Phase 4 routers** — `/display.bmp`, `/display.png`, `/cache/status`
4. **Write Phase 5 tests** — Unit + integration with 95% coverage
5. **Deploy Phase 6** — Docker, Kubernetes, ESPHome config

## References

- [FastAPI Lifespan Pattern](https://fastapi.tiangolo.com/advanced/events/)
- [Pillow Image Mode '1' (B/W)](https://pillow.readthedocs.io/en/stable/handbook/concepts.html#image-modes)
- [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest)
- [InfluxDB Flux API](https://docs.influxdata.com/influxdb/cloud/query-data/get-started/)
- [Google Calendar API](https://developers.google.com/calendar/api)
