.PHONY: help dev install test test-fast test-integration test-all lint typecheck validate check \
	docker-build docker-run docker-push k8s-deploy k8s-delete k8s-logs k8s-status env clean

GREEN := \033[0;32m
NC    := \033[0m

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

# ── Development ───────────────────────────────────────────────────────────────

install: ## Install Python dependencies
	uv sync --all-extras

dev: ## Start development server on :8000 with hot reload
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# ── Testing & Quality ─────────────────────────────────────────────────────────

test: ## Run tests with coverage (≥95% required)
	uv run pytest --cov=src --cov-fail-under=95

test-fast: ## Run tests without coverage
	uv run pytest --cov-fail-under=0

test-integration: ## Run integration tests (requires Docker)
	uv run pytest tests/integration -v -m integration

test-all: test test-integration ## Run all tests including integration

lint: ## Run ruff linter
	uv run ruff check src tests

typecheck: ## Run mypy type checking
	uv run mypy src

validate: lint typecheck ## Run ruff + mypy only (no tests)

check: lint typecheck test ## Run lint + typecheck + test

# ── Docker ────────────────────────────────────────────────────────────────────

docker-build: ## Build Docker image
	docker build -t inknook-backend:latest .

docker-run: docker-build ## Run Docker container locally
	docker run -p 8000:8000 \
		-e HA_URL=http://home-assistant:8123 \
		-e HA_TOKEN=$${HA_TOKEN} \
		-e INFLUXDB_URL=http://influxdb:8086 \
		-e INFLUXDB_TOKEN=$${INFLUXDB_TOKEN} \
		-e INFLUXDB_BUCKET=home \
		-e INFLUXDB_ORG=my-org \
		-e GOOGLE_SERVICE_ACCOUNT_JSON_B64=$${GOOGLE_SERVICE_ACCOUNT_JSON_B64} \
		inknook-backend:latest

docker-push: docker-build ## Push image to registry (requires IMAGE_REPO)
	docker tag inknook-backend:latest $${IMAGE_REPO}/inknook-backend:latest
	docker push $${IMAGE_REPO}/inknook-backend:latest

# ── Kubernetes ────────────────────────────────────────────────────────────────

k8s-deploy: ## Deploy to Kubernetes
	kubectl apply -f kubernetes.yaml
	kubectl wait --for=condition=available --timeout=300s \
		deployment/inknook-backend -n inknook-backend

k8s-delete: ## Delete Kubernetes deployment
	kubectl delete -f kubernetes.yaml

k8s-logs: ## Tail logs from Kubernetes pods
	kubectl logs -n inknook-backend -l app=inknook-backend -f

k8s-status: ## Show Kubernetes deployment status
	kubectl get pods -n inknook-backend
	kubectl get svc -n inknook-backend
	kubectl describe deployment -n inknook-backend inknook-backend

# ── Utilities ─────────────────────────────────────────────────────────────────

env: ## Show required environment variables
	@echo "$(GREEN)Home Assistant$(NC):   HA_URL, HA_TOKEN"
	@echo "$(GREEN)InfluxDB$(NC):         INFLUXDB_URL, INFLUXDB_TOKEN, INFLUXDB_BUCKET, INFLUXDB_ORG"
	@echo "$(GREEN)Google Calendar$(NC):  GOOGLE_SERVICE_ACCOUNT_JSON_B64"
	@echo "See .env.example for full reference"

clean: ## Remove build artifacts
	rm -rf .venv build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -f .coverage htmlcov
