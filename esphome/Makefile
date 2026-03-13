CONFIG := epaper.yaml

ESPHOME := /home/stevendejong/workspace/personal/home-automation/esphome/.venv/bin/esphome

.PHONY: flash flash-usb flash-ota compile logs validate clean dashboard

flash: flash-usb ## Compile and upload via USB (default)

flash-usb: ## Compile and upload via USB (/dev/ttyUSB0)
	$(ESPHOME) run $(CONFIG) --device /dev/ttyUSB0

flash-ota: ## Compile and upload via OTA (WiFi)
	$(ESPHOME) run $(CONFIG) --device inknook-dashboard.local

compile: ## Compile firmware without uploading
	$(ESPHOME) compile $(CONFIG)

logs: ## Stream serial logs from the device
	$(ESPHOME) logs $(CONFIG)

validate: ## Validate config YAML without compiling
	$(ESPHOME) config $(CONFIG)

clean: ## Remove build artifacts
	rm -rf .esphome/build

dashboard: ## Open ESPHome dashboard in browser (runs local web UI)
	$(ESPHOME) dashboard .

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
