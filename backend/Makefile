.PHONY: help dev test lint typecheck build docker-build docker-run k8s-deploy k8s-delete clean

# Colors for output
GREEN := \033[0;32m
BLUE := \033[0;34m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)inknook-backend - E-paper dashboard service$(NC)"
	@echo ""
	@echo "$(GREEN)Development$(NC)"
	@echo "  make dev              Start development server (reload on changes)"
	@echo "  make install          Install dependencies"
	@echo ""
	@echo "$(GREEN)Testing & Quality$(NC)"
	@echo "  make test             Run tests with coverage"
	@echo "  make test-fast        Run tests without coverage"
	@echo "  make lint             Run ruff linter"
	@echo "  make typecheck        Run mypy type checking"
	@echo "  make check            Run all linting and type checks"
	@echo ""
	@echo "$(GREEN)Docker$(NC)"
	@echo "  make docker-build     Build Docker image"
	@echo "  make docker-run       Run Docker container locally"
	@echo "  make docker-push      Push to registry (requires IMAGE_REPO)"
	@echo ""
	@echo "$(GREEN)Kubernetes$(NC)"
	@echo "  make k8s-deploy       Deploy to Kubernetes"
	@echo "  make k8s-delete       Delete Kubernetes deployment"
	@echo "  make k8s-logs         Tail logs from pods"
	@echo "  make k8s-status       Show deployment status"
	@echo ""
	@echo "$(GREEN)Utilities$(NC)"
	@echo "  make clean            Clean build artifacts"
	@echo "  make env              Show environment variables needed"

install:
	uv sync --all-extras

dev:
	uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	uv run pytest --cov=src --cov-fail-under=95

test-fast:
	uv run pytest --cov-fail-under=0

test-integration:
	@echo "$(BLUE)Running integration tests (requires Docker)$(NC)"
	uv run pytest tests/integration -v -m integration

test-all: test test-integration

lint:
	uv run ruff check src tests

typecheck:
	uv run mypy src

check: lint typecheck test

docker-build:
	docker build -t inknook-backend:latest .

docker-run: docker-build
	docker run -p 8000:8000 \
		-e HA_URL=http://home-assistant:8123 \
		-e HA_TOKEN=$${HA_TOKEN} \
		-e INFLUXDB_URL=http://influxdb:8086 \
		-e INFLUXDB_TOKEN=$${INFLUXDB_TOKEN} \
		-e INFLUXDB_BUCKET=home \
		-e INFLUXDB_ORG=my-org \
		-e GOOGLE_SERVICE_ACCOUNT_JSON_B64=$${GOOGLE_SERVICE_ACCOUNT_JSON_B64} \
		inknook-backend:latest

docker-push: docker-build
	docker tag inknook-backend:latest $${IMAGE_REPO}/inknook-backend:latest
	docker push $${IMAGE_REPO}/inknook-backend:latest

k8s-deploy:
	kubectl apply -f kubernetes.yaml
	kubectl wait --for=condition=available --timeout=300s \
		deployment/inknook-backend -n inknook-backend

k8s-delete:
	kubectl delete -f kubernetes.yaml

k8s-logs:
	kubectl logs -n inknook-backend -l app=inknook-backend -f

k8s-status:
	kubectl get pods -n inknook-backend
	kubectl get svc -n inknook-backend
	kubectl describe deployment -n inknook-backend inknook-backend

env:
	@echo "$(BLUE)Environment Variables Required$(NC)"
	@echo ""
	@echo "Home Assistant:"
	@echo "  HA_URL=http://home-assistant:8123"
	@echo "  HA_TOKEN=your-ha-long-lived-token"
	@echo ""
	@echo "InfluxDB:"
	@echo "  INFLUXDB_URL=http://influxdb:8086"
	@echo "  INFLUXDB_TOKEN=your-influxdb-token"
	@echo "  INFLUXDB_BUCKET=home"
	@echo "  INFLUXDB_ORG=my-org"
	@echo ""
	@echo "Google Calendar (base64-encoded service account JSON):"
	@echo "  GOOGLE_SERVICE_ACCOUNT_JSON_B64=your-base64-encoded-json"
	@echo ""
	@echo "See .env.example for full reference"

clean:
	rm -rf .venv build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -f .coverage htmlcov
