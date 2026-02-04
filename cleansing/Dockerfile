# Stage 1: UV and dependency installation
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS uv-base
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies into virtual environment
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Stage 2: Final minimal image
FROM python:3.13-slim
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from uv-base stage
COPY --from=uv-base /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application code
COPY dlt_project/ ./dlt_project/
COPY scripts/ ./scripts/
COPY pyproject.toml uv.lock .python-version ./

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import dlt; print('dlt version:', dlt.__version__)" || exit 1

# Set entry point
ENTRYPOINT ["python", "-m", "dlt_project.pipeline"]