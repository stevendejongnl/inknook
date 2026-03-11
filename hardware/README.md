# Hardware

## Bill of Materials

| Component | Model | Notes |
|-----------|-------|-------|
| Microcontroller | DFRobot FireBeetle 2 ESP32-E | Built-in LiPo charger, low-power design |
| Display | Waveshare 7.5" e-Paper V2 (B/W) | 800×480, ~26mA active, 0µA standby |
| Display HAT | Waveshare e-Paper ESP32 Driver Board | Or wire directly — see pin table below |
| Environment sensor | BME280 | Temperature, humidity, pressure over I2C |
| Battery | LiPo 3.7V 2000–4000mAh | JST-PH 2.0 connector for FireBeetle |
| Enclosure | A4 photo frame (~21×15cm) | Display fits 7.5" panel; ESP32 mounts behind |

---

## Wiring

### SPI — Display (Waveshare 7.5" V2)

| Signal | ESP32 GPIO | Notes |
|--------|-----------|-------|
| SCK    | GPIO18    | SPI clock |
| MOSI   | GPIO23    | SPI data |
| CS     | GPIO13    | Chip select |
| DC     | GPIO22    | Data/command |
| RST    | GPIO21    | Reset |
| BUSY   | GPIO14    | Busy signal (active LOW on V2 — `busy_pin_inverted: true` in ESPHome) |
| PWR    | GPIO26    | Display power enable — set HIGH before SPI init |
| GND    | GND       | |
| 3.3V   | 3.3V      | |

> **V2 note:** The BUSY pin is active LOW on Waveshare 7.5" V2. ESPHome's `busy_pin_inverted: true` is required — without it the driver waits forever and the display corrupts.

### I2C — BME280

| Signal | ESP32 GPIO | Notes |
|--------|-----------|-------|
| SDA    | GPIO17    | |
| SCL    | GPIO16    | |
| VCC    | 3.3V      | |
| GND    | GND       | |
| ADDR   | GND       | Sets I2C address to 0x76 |

### Battery ADC

| Signal | ESP32 GPIO | Notes |
|--------|-----------|-------|
| VBAT   | GPIO35 (A2) | Via 1:1 voltage divider (2× 100kΩ) — reads half of battery voltage |

Voltage formula: `V_bat = ADC_raw_voltage × 2`

The FireBeetle 2 has a built-in voltage divider on A2 connected to the JST battery input. No external resistors needed if using the onboard JST connector.

---

## Power budget

| State | Current | Duration |
|-------|---------|----------|
| Deep sleep | ~10µA | 29–30 min per cycle |
| Active (WiFi + fetch + render) | ~80–150mA | ~15–30s per cycle |
| Display refresh | +26mA | ~3s |

Estimated battery life at 30-minute intervals, 6AM–midnight (18h/day):
- **2000mAh LiPo → ~3–4 weeks**
- **4000mAh LiPo → ~6–8 weeks**

---

## Assembly notes

1. Mount the Waveshare display panel in the photo frame, facing glass
2. Route the FPC cable through the frame backing
3. Connect FPC to the Driver Board or direct wiring harness
4. Mount ESP32 behind the frame with foam tape or a small 3D-printed bracket
5. Run a short JST LiPo cable to the FireBeetle's battery connector
6. The FireBeetle's USB-C port can remain accessible at the frame edge for OTA + charging
