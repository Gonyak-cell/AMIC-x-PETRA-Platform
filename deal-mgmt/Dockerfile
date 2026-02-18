# =============================================================================
# Deal Management Service
# Multi-stage Docker build
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies with uv
# ---------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (layer caching)
COPY pyproject.toml uv.lock ./

# Export requirements and install to /install prefix (survives bind mounts)
RUN uv export --frozen --no-dev --no-hashes > requirements.txt \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# Copy application source code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# ---------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim-bookworm AS runtime

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 dealmgmt \
    && useradd --uid 1000 --gid dealmgmt --shell /bin/bash --create-home dealmgmt

# Copy installed packages from builder (to system Python — outside /app)
COPY --from=builder /install/lib /usr/local/lib
COPY --from=builder /install/bin /usr/local/bin

# Copy application code from builder
COPY --from=builder /build/app /app/app
COPY --from=builder /build/migrations /app/migrations
COPY --from=builder /build/alembic.ini /app/alembic.ini

# Copy entrypoint script
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
RUN chown -R dealmgmt:dealmgmt /app
USER dealmgmt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/docker-entrypoint.sh"]
