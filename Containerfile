# =============================================================================
# eco-x Containerfile - Multi-Stage Build with uv
# =============================================================================
# Build: podman build -t eco-x:latest .
# Run:   podman run -d -p 8000:8000 -v ./data:/app/data:Z eco-x:latest
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Build - Install dependencies with uv
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (without dev dependencies, without the project itself)
RUN uv sync --frozen --no-dev --no-install-project

# Copy source code and install the project
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini ./
RUN uv sync --frozen --no-dev

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Create non-root user for security
RUN groupadd --gid 1000 ecox && \
    useradd --uid 1000 --gid 1000 --shell /bin/bash --create-home ecox

# Install only runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

# Copy runtime assets
COPY static/ static/
COPY templates/ templates/
COPY config/ config/
COPY locales/ locales/

# Create data directory and set ownership
RUN mkdir -p /app/data && chown -R ecox:ecox /app

# Configure environment
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER ecox

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "data_fetchers.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
