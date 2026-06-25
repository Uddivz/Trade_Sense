# TradeSense Backend — Dockerfile
# Multi-stage build: keeps the production image lean

# ── Stage 1: Builder ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system dependencies required for asyncpg and cryptography
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install Python dependencies into a local prefix
COPY requirements.txt .
RUN uv pip install --system --prefix=/install --no-cache -r requirements.txt


# ── Stage 2: Production Runtime ─────────────────────────────────────────────────
FROM python:3.12-slim AS production

WORKDIR /app

# Create non-root user for security
RUN addgroup --system tradesense && adduser --system --ingroup tradesense tradesense

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Change ownership
RUN chown -R tradesense:tradesense /app
USER tradesense

# Expose FastAPI port
EXPOSE 8000

# Health check — Docker polls this every 30s
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health', timeout=5); exit(0 if r.status_code == 200 else 1)"

# Start with uvicorn
# Use --workers 1 in development; increase to --workers 4 in production
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "info"]
