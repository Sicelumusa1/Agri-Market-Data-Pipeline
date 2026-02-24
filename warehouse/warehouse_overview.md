# Warehouse Overview

## Design Philosophy
Our warehouse follows an **ELT (Extract-Load-Transform)** pattern optimized for BigQuery's architecture:

1. **Extract & Load**: dlt loads raw CSV files from GCS to BigQuery (silver layer)
2. **Transform**: dbt transforms within BigQuery (gold layer)
3. **Serve**: Looker Studio queries pre-aggregated gold tables

## Why ELT over ETL?
| **Approach** | **Why We Chose ELT** |
|-------------|----------------------|
| **Compute location** | Transform inside BigQuery (massively parallel) vs external processing |
| **Cost model** | BigQuery charges by query, not by server uptime |
| **Scale** | Petabyte-scale without cluster management |
| **Simplicity** | SQL-only transformations, no Spark clusters |

## Layer Responsibilities

### Silver Layer (`silver_layer.md`)
- **Purpose**: "Cleaned but still raw"
- **Source**: GCS bronze files → dlt
- **Characteristics**:
  - Standardized data types (dates, currencies, quantities)
  - Parsed product combinations (variety, class, size, color)
  - Schema evolution handled (new columns don't break pipeline)
  - **Not** aggregated, **not** business-logic applied

### Gold Layer (`gold_layer.md`)
- **Purpose**: "Decision-ready intelligence"
- **Source**: Silver layer → dbt
- **Characteristics**:
  - Pre-aggregated for speed
  - Denormalized star schema (dimensions embedded in facts)
  - Farmer-question driven (each table answers one question)
  - Partitioned and clustered for cost efficiency

## How dbt Fits
dbt is the transformation engine that:
1. Reads from silver tables (already cleaned)
2. Applies business logic (calculations, rankings, recommendations)
3. Writes to gold tables (materialized for dashboard consumption)
4. Tests data quality (schema.yml tests)

## How Looker Studio Consumes
Looker Studio queries **only gold tables** because:
-  Fastest response times (pre-aggregated, denormalized)
-  Cheapest queries (scan less data)
-  Simplest for farmers (one table per dashboard page)
-  Secure (raw data never exposed)

## Update Cadence
| **Layer** | **Update Frequency** | **Trigger** |
|----------|---------------------|------------|
| Bronze | Daily | New CSV files in GCS |
| Silver | Daily | dlt pipeline (post-ingestion) |
| Gold | Daily + On-demand | dbt runs (scheduled + manual) |