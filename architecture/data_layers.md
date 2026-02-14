# Data Layer Architecture

## Bronze Layer – Raw Data Lake

### Purpose
The Bronze layer stores raw market data exactly as received from source systems. No transformations are applied at this stage.

### Storage
- Google Cloud Storage
- CSV format
- File-based ingestion

### Bucket Structure

gs://market-data-bucket/
├── joburg-market/
│ ├── summary/
│ │ └── summary.csv
│ ├── container/
│ │ └── container.csv
│ └── variety/
│ └── variety.csv
├── pretoria-market/ # future
│ └── ...
└── UPLOAD_DONE


### Design Decisions
- **Market-level folders** enable independent scaling
- **File-type folders** simplify parallel processing
- **Immutable raw files** support reprocessing and auditing
- **Completion marker** guarantees dataset completeness

### Characteristics
- Append-only
- No schema enforcement
- Original format preserved
- Cold storage optimized for cost

---

## Silver Layer – Cleaned & Standardized Data

### Purpose
Transform raw CSV files into clean, typed, analytics-ready datasets.

### Tooling
- dlt (Python-based data pipelines)

### BigQuery Structure

project: market-data
dataset: silver_layer

tables:

to be determined


### Core Transformations
1. Split combined fields into atomic columns
2. Normalize date formats (YYYY-MM-DD)
3. Parse and clean decimal values
4. Standardize currency and quantities
5. Normalize commodity naming
6. Enforce consistent null handling

### dlt Capabilities Leveraged
- Schema drift handling
- Parquet intermediate storage
- Automatic type inference
- Parallel file processing

### Characteristics
- Columnar storage
- Schema-enforced
- Analytics-ready
- Reusable across downstream models

---

## Gold Layer – Analytics & Business Logic

### Purpose
Expose business-ready metrics optimized for analytical queries and dashboards.

### Tooling
- dbt (SQL-only transformations)

### Dataset Structure

project: market-data
dataset: gold_layer

tables:

to be determined


### Partitioning Strategy
PARTITION BY DATE(transaction_date)

Rationale: Most queries filter by date ranges.

### Clustering Strategy

CLUSTER BY
  market,
  commodity_category,
  day_of_week,
  week_of_month,
  season

#### Supports:

Seasonal trend analysis

Day-of-week price behavior

Market-to-market comparisons

### Data Lineage

Raw CSV
  → Bronze (GCS)
    → Silver (BigQuery)
      → Gold (BigQuery)
        → Materialized Views
          → Looker Studio

### Data Quality Enforcement

Bronze: File presence & format validation

Silver: Type enforcement, null thresholds

Gold: Business rule validation via dbt tests
