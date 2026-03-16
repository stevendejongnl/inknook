# Multi-stage build for inknook-backend

# Stage 1: Builder
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml pyproject.toml
COPY README.md README.md
COPY src src

# Build virtual environment with uv
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Install the package and all its dependencies (registers metadata so version() works)
RUN uv pip install .

# Stage 2: Runtime
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (fonts for image rendering)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code and sensor config
COPY src src
COPY sensors.yaml sensors.yaml

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Set environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
