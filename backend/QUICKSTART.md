# Quick Start Guide

## Local Development

### 1. Install Dependencies

```bash
make install
# or: uv sync --all-extras
```

### 2. Configure Environment

Copy and fill in credentials:

```bash
cp .env.example .env
# Edit .env with your Home Assistant URL/token, InfluxDB credentials, Google Calendar JSON
```

**Required variables**:
- `HA_URL` — Home Assistant base URL (e.g., `http://home-assistant:8123`)
- `HA_TOKEN` — Long-lived access token
- `INFLUXDB_URL` — InfluxDB URL (e.g., `http://influxdb:8086`)
- `INFLUXDB_TOKEN` — API token
- `GOOGLE_SERVICE_ACCOUNT_JSON_B64` — Base64-encoded service account JSON

### 3. Run Development Server

```bash
make dev
# or: uv run uvicorn src.main:app --reload --port 8000
```

Server runs at `http://localhost:8000`

### 4. Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# View dashboard
curl http://localhost:8000/display.bmp -o dashboard.bmp
open dashboard.bmp

# Check cache status
curl http://localhost:8000/cache/status | jq
```

---

## Testing

```bash
# Run all tests with coverage
make test

# Run tests without coverage check
make test-fast

# Run specific test file
uv run pytest tests/test_cache.py -v

# Run with logs
uv run pytest tests/test_routers.py -v -s
```

---

## Code Quality

```bash
# Lint code (ruff)
make lint

# Type checking (mypy)
make typecheck

# Run all checks
make check
```

---

## Docker

### Build Image

```bash
make docker-build
# or: docker build -t inknook-backend:latest .
```

### Run Locally

```bash
make docker-run
# Requires: HA_TOKEN, INFLUXDB_TOKEN, GOOGLE_SERVICE_ACCOUNT_JSON_B64 env vars
```

---

## Kubernetes Deployment

### 1. Edit Secrets

Update `kubernetes.yaml` with real credentials:

```yaml
stringData:
  HA_TOKEN: "your-token-here"
  INFLUXDB_TOKEN: "your-token-here"
  GOOGLE_SERVICE_ACCOUNT_JSON_B64: "your-base64-json-here"
```

### 2. Build and Push Image

```bash
docker build -t your-registry/inknook-backend:latest .
docker push your-registry/inknook-backend:latest
```

Update `kubernetes.yaml` image reference if using custom registry.

### 3. Deploy

```bash
make k8s-deploy

# Verify deployment
make k8s-status

# View logs
make k8s-logs
```

### 4. Access Service

```bash
# Port forward for testing
kubectl port-forward -n inknook-backend svc/inknook-backend 8000:8000

# Then access: http://localhost:8000/display.bmp
```

---

## ESPHome Integration

Configure ESPHome to fetch BMP from backend:

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
    lambda: |-
      // Fetch BMP every 10 minutes
      http_client.get("http://inknook-backend:8000/display.bmp");
```

---

## Troubleshooting

### "Failed to fetch from Home Assistant"

- Check `HA_URL` and `HA_TOKEN` in `.env`
- Verify Home Assistant is accessible from backend

### "Failed to query InfluxDB"

- Check `INFLUXDB_URL` and `INFLUXDB_TOKEN`
- Verify bucket and org names
- Check InfluxDB is accessible

### "No upcoming events"

- Check `GOOGLE_SERVICE_ACCOUNT_JSON_B64` is valid base64
- Ensure service account has Calendar API access
- Verify calendar exists and is shared with service account

### "Cache status shows errors"

- Check `/cache/status` endpoint for detailed error messages
- Invalid data shows as error dict, not exception
- Data is missing/incomplete when sources are unreachable

### Kubernetes pod fails to start

```bash
# Check logs
kubectl logs -n inknook-backend -l app=inknook-backend

# Check events
kubectl describe pod -n inknook-backend <pod-name>

# Verify secrets
kubectl get secrets -n inknook-backend
```

---

## Useful Commands

```bash
# Show help
make help

# Show environment variables needed
make env

# Clean build artifacts
make clean

# View live logs (k8s)
make k8s-logs

# Get deployment status (k8s)
make k8s-status

# Delete deployment (k8s)
make k8s-delete
```

---

## Next Steps

1. ✅ **Local testing** — Get the server running locally and verify `/display.bmp`
2. ✅ **Docker verification** — Build and test Docker image locally
3. **Kubernetes deployment** — Deploy to your cluster
4. **ESPHome config** — Flash ESP32 with updated config
5. **Display verification** — Check e-paper display updates every 10 minutes

---

## Documentation

- **Full Architecture**: See `README.md`
- **Implementation Details**: See inline code comments
- **API Docs**: http://localhost:8000/docs (Swagger UI when server running)
