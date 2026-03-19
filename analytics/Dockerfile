# ---------- Builder ----------
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    dbt-core==1.8.0 \
    dbt-bigquery==1.8.0


# ---------- Runtime ----------
FROM python:3.11-slim

# Python runtime optimizations
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy Python environment
COPY --from=builder /usr/local /usr/local

# Install runtime git
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# dbt environment
ENV DBT_PROFILES_DIR=/app/dbt
ENV DBT_PROJECT_DIR=/app

# Copy dependency file first for caching
COPY dbt_project.yml packages.yml ./

RUN dbt deps

# Copy project
COPY . .

# Pre-parse dbt project
RUN dbt ls > /dev/null 2>&1 || true

# Create non-root user
RUN useradd -m -d /home/dbtuser -s /bin/bash dbtuser \
    && chown -R dbtuser:dbtuser /app

USER dbtuser

CMD ["dbt"]