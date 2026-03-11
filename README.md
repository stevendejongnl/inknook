# Inknook

A wall-mounted e-paper dashboard in a photo frame. Displays weather, sensor readings, and calendar events — fetched from Home Assistant and rendered as a 800×480 black-and-white image by a FastAPI backend.

## How it works

```
Home Assistant  ──┐
InfluxDB        ──┼──▶  backend (FastAPI)  ──▶  /display.bmp  ◀──  ESP32 (ESPHome)  ──▶  e-paper display
Google Calendar ──┘         (Kubernetes)                               deep sleep 30min
```

1. The **backend** fetches live data, renders an 800×480 BMP, and serves it at `/display.bmp`
2. The **ESP32** wakes every 30 minutes (6 AM–midnight), fetches the BMP over WiFi, pushes it to the display, then goes back to deep sleep
3. The **BME280** sensor on the ESP32 publishes temperature, humidity, and pressure back to Home Assistant via the native API

## Repository layout

```
inknook/
├── backend/        FastAPI service — data fetching, rendering, Kubernetes manifests
├── esphome/        ESPHome firmware config for the ESP32
└── hardware/       Pin wiring, BOM, and assembly notes
```

## Quick start

**Backend (local dev):**
```bash
cd backend
cp .env.example .env   # fill in HA_TOKEN, INFLUXDB_TOKEN, etc.
make dev               # starts on http://localhost:8000
open http://localhost:8000/display.png
```

**Firmware:**
```bash
cd esphome
cp secrets.yaml.example secrets.yaml   # fill in WiFi + backend URL
esphome compile epaper.yaml
esphome upload epaper.yaml
esphome logs epaper.yaml
```

See [`backend/README.md`](backend/README.md) and [`backend/QUICKSTART.md`](backend/QUICKSTART.md) for full documentation.
