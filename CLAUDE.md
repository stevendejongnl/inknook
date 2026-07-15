# inknook — E-Paper Dashboard

800×480 B/W e-paper dashboard: ESP32 (ESPHome) fetches a BMP from a Python backend, renders it, then deep-sleeps 30 min.

## Project Layout

```
esphome/   — ESP32 firmware (epaper.yaml)
backend/   — FastAPI image renderer (Python/uv)
```

## ESPHome (firmware)

All commands run from `esphome/`:

| Command | Action |
|---------|--------|
| `make` | Show help |
| `make flash-ota` | Compile + upload via OTA (WiFi) — default for day-to-day flashing |
| `make flash-usb` | Compile + upload via USB (`/dev/ttyUSB0`) — use when OTA unreachable |
| `make compile` | Compile without uploading |
| `make validate` | Validate YAML config (fast, no compile) |
| `make logs` | Stream serial logs |
| `make clean` | Remove build artifacts |
| `make dashboard` | Open ESPHome web UI |

**Deep sleep and OTA**: The device deep-sleeps between render cycles so OTA (`flash-ota`) usually
fails — the device isn't reachable. Use `make flash-usb` (USB cable) for routine firmware updates.
OTA only works if you pre-compile (`make compile`) and then press RST to wake the device and
immediately run `make flash-ota` within the ~90s awake window before it sleeps again.

ESPHome binary: `/home/stevendejong/workspace/personal/home-automation/esphome/.venv/bin/esphome`

## Backend (Python)

All commands run from `backend/`:

| Command | Action |
|---------|--------|
| `make dev` | Start dev server on :8000 with hot reload |
| `make test` | Run tests with coverage (≥95% required) |
| `make check` | lint + typecheck + test |
| `make validate` | ruff + mypy only |

## Display Layout (800×480)

```
┌────────────────┬────────────────┐
│  Weather       │  Sensors       │  0–240px
├────────────────┴────────────────┤
│  Calendar (today │ next 3 days) │  240–448px
├─────────────────────────────────┤
│  Status bar (ESPHome draws)     │  448–480px
└─────────────────────────────────┘
```

The backend reserves the bottom 32px (`BOTTOM_BAR_HEIGHT`). ESPHome draws the live
battery%, WiFi RSSI, and last-update time over that region after loading the image.

## Kubernetes

Manifests live in `kubernetes/`. Apply with local kubectl (kubeconfig at `~/.kube/config`):

```bash
kubectl apply -f kubernetes/keel.yaml     # one-time: deploy Keel image watcher
kubectl apply -f backend/kubernetes.yaml  # deploy/update inknook backend
```

**SSH to nodes**: Use `SSH_AUTH_SOCK=~/.1password/agent.sock ssh kubernetes-master-01` (1Password SSH agent, user `root`). The local `~/.ssh/id_rsa` is corrupt — always use the agent.

**Auto-redeployment (Keel)**: `kubernetes/keel.yaml` runs Keel in the `keel` namespace. It polls container registries every 5 min and triggers a rolling restart when the image digest changes. Opt a deployment in by adding to `spec.template.metadata.annotations`:
```yaml
keel.sh/policy: force
keel.sh/trigger: poll
keel.sh/pollSchedule: "@every 5m"
```

## Battery Thresholds

- Battery: BLY 523450, 3.7V nominal, 1000mAh, cutoff 2.75V
- LiPo range: 3.0V (empty) → 4.2V (full)
- Low battery guard: `< 3.1V` (~8%) — skips fetch, shows warning screen, sleeps 4h
- ADC pin: GPIO35 (A2) with ×2 filter for voltage divider
