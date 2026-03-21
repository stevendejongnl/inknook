CONFIG := inknook.yaml
ESPHOME := /home/stevendejong/workspace/personal/home-automation/esphome/.venv/bin/esphome
PYTHON  := /home/stevendejong/workspace/personal/home-automation/esphome/.venv/bin/python
UV_PROJECT := /home/stevendejong/workspace/personal/home-automation/esphome
DEVICE_IP := $(shell grep '^inknook_device_ip:' secrets.yaml | awk '{gsub(/"/, "", $$2); print $$2}')
HA_HOST := root@192.168.1.25
HA_CONFIG_PATH := /config/esphome/inknook.yaml

.PHONY: flash flash-usb flash-ota compile logs validate clean dashboard upload-ha upgrade _check-upgrade

# Check current vs latest ESPHome version and offer to upgrade
_check-upgrade:
	@CURRENT=$$($(ESPHOME) version | grep -oP '[\d]+\.[\d]+\.[\d]+'); \
	LATEST=$$($(PYTHON) -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('https://pypi.org/pypi/esphome/json').read()); print(d['info']['version'])"); \
	echo "  ESPHome: current=$$CURRENT  latest=$$LATEST"; \
	if [ "$$CURRENT" != "$$LATEST" ]; then \
		printf "  Upgrade to $$LATEST before flashing? [y/N] "; read ans; \
		if [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]; then \
			$(MAKE) upgrade; \
		fi \
	fi

upgrade: ## Upgrade ESPHome to the latest version
	cd $(UV_PROJECT) && uv add "esphome>=2026" --upgrade-package esphome
	@echo "  ESPHome upgraded to $$($(ESPHOME) version)"

flash: _check-upgrade flash-usb ## Compile and upload via USB (default)

flash-usb: _check-upgrade ## Compile and upload via USB (/dev/ttyUSB0)
	$(ESPHOME) run $(CONFIG) --device /dev/ttyUSB0

flash-ota: _check-upgrade ## Compile first, then prompt to hit RST before uploading via OTA
	$(ESPHOME) compile $(CONFIG)
	@echo ""
	@echo "  Firmware compiled."
	@echo "  Press RST 3x rapidly to enter safe mode (OTA-only), then hit Enter to upload ($(DEVICE_IP))..."
	@read _
	@echo "  Waiting for device to boot..."
	@sleep 45
	$(ESPHOME) upload $(CONFIG) --device $(DEVICE_IP)

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

upload-ha: ## Upload inknook.yaml to Home Assistant ESPHome config
	scp -P 24 $(CONFIG) $(HA_HOST):$(HA_CONFIG_PATH)
	@echo "  Uploaded $(CONFIG) → $(HA_HOST):$(HA_CONFIG_PATH)"

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
