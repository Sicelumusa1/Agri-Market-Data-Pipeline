# Build stage
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./

# Install dependencies in a separate layer with cache mount
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

# Copy source code
COPY dlt_project/ ./dlt_project/
COPY scripts/ ./scripts/

# Final install
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Runtime stage
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    libstdc++6 \
    libgcc-s1 \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /app /app

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/output && \
    chown appuser:appuser /app/data /app/output

ENV PATH="/app/.venv/bin:$PATH"
USER appuser

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import dlt, google.cloud; print('dlt version:', dlt.__version__)" || exit 1

ENTRYPOINT ["python", "/app/scripts/run_pipeline.py"]