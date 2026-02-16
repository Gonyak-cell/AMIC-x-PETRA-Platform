# =============================================================================
# Auto FDD - Financial Due Diligence Backend
# Multi-stage Docker build
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Copy dependency files first (layer caching)
COPY pyproject.toml ./

# Install production dependencies only
RUN pip install --no-cache-dir --prefix=/install .

# Copy application source code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# ---------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# ---------------------------------------------------------------------------
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 autofdd \
    && useradd --uid 1000 --gid autofdd --shell /bin/bash --create-home autofdd

# Copy installed packages from builder
COPY --from=builder /install/lib /usr/local/lib
COPY --from=builder /install/bin /usr/local/bin

# Copy application code from builder
COPY --from=builder /build/app /app/app
COPY --from=builder /build/alembic /app/alembic
COPY --from=builder /build/alembic.ini /app/alembic.ini

# Copy entrypoint script
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# Create uploads directory
RUN mkdir -p /app/uploads

ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
RUN chown -R autofdd:autofdd /app
USER autofdd

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["/app/docker-entrypoint.sh"]
