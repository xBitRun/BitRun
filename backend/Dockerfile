# BITRUN Backend Dockerfile
# Multi-stage build for Python FastAPI application

# ============================================================
# Stage 1: Builder - install dependencies with build tools
# ============================================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Install build dependencies with retry mechanism
RUN set -eux; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends --fix-missing build-essential && \
        break || sleep 10; \
    done && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================================
# Stage 2: Development - full environment with build tools
# ============================================================
FROM python:3.12-slim AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime + dev dependencies with retry mechanism
RUN set -eux; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends --fix-missing curl build-essential && \
        break || sleep 10; \
    done && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ============================================================
# Stage 3: Production - minimal runtime image
# ============================================================
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install only runtime dependencies with retry mechanism
RUN set -eux; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends --fix-missing curl && \
        break || sleep 10; \
    done && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder (no build tools needed)
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
