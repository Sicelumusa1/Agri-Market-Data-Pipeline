# Silver Layer Documentation

## What is Silver?
The silver layer represents **cleaned, standardized, analytics-ready raw data**. It is the first point where data becomes usable for analysis, but it is **not yet optimized for specific business questions**.

## Key Characteristics
| **Attribute** | **Description** |
|--------------|-----------------|
| **Grain** | Transaction-level (one row per market entry) |
| **Source** | dlt pipeline from GCS bronze files |
| **Destination** | BigQuery dataset: `silver` |
| **Update** | Daily, full refresh (replace) |
| **Access** | dbt models only (not exposed to dashboards) |

## Data Processing Steps in dlt

### 1. File-Based Ingestion

dlt handles:
- Reading CSV files from GCS bucket
- Detecting schema from file headers
- Handling missing/extra columns

### 2. Data Type Standardization
|Original   |   Standardized   |     Method |
|-------------------|---------------|-----------------------|
|"19 January 2026"  |	2026-01-19  |	pd.to_datetime()    |
|"R3,311,589.00"    |	3311589.00  |	Remove 'R', commas, cast to float   |
|"R-8,320.00"   |	-8320.00    |	Handle negative values  |
|"16,335MTD: 150,488"   |	daily:16335, mtd:150488 |	Split combined fields   |

### 3. Product Combination Parsing

Complex strings like "AFRI BLUSH,CL 1,150,8,RED" are parsed into:
- variety: "AFRI BLUSH"
- class: "CL 1" 
- size: 150
- count: 8
- color: "RED"

### 4. Schema Drift Handling

dlt automatically detects and handles:

- New columns appearing in CSV files

- Changed data types

- Missing columns

- All without pipeline failure

### Silver Schema: silver_enriched_data
```sql
CREATE TABLE silver.silver_enriched_data (
    -- Identifiers
    ingestion_run_id STRING,
    source_file STRING,
    link_type STRING,  -- 'summary', 'container', 'variety'
    
    -- Time dimensions
    scrape_date DATE,
    ingestion_timestamp TIMESTAMP,
    
    -- Product dimensions
    commodity STRING,
    variety STRING,
    container_type STRING,
    class STRING,
    size_value STRING,
    color STRING,
    
    -- Measures (standardized)
    total_value_sold FLOAT64,
    total_qty_sold FLOAT64,
    total_kg_sold FLOAT64,
    qty_available FLOAT64,
    average_price_per_kg FLOAT64,
    highest_price_per_kg FLOAT64,
    unit_mass FLOAT64,
    
    -- Parsed components
    size_numeric INT64,
    size_category STRING,
    container_kg FLOAT64,
    
    -- Metadata
    data_quality_flag STRING,
    validation_errors STRING
)
PARTITION BY scrape_date
CLUSTER BY commodity, link_type;
```

### Why Silver is NOT for Dashboards

Silver tables are analytics-ready but:

- Too granular (transaction-level, slow to query)

- Not aggregated (every query recalculates totals)

- Complex joins required (need to combine with other tables)

- Exposed to schema changes (new columns could break dashboards)

### Who Can Query Silver?

- dbt models (for transformation)

- Data engineers (for debugging)

- Analysts (with approval)

- Looker Studio (never)

- Farmers (never)

### Data Quality Checks
-- Every silver load validates:
1. No nulls in required fields (scrape_date, commodity)
2. Positive values for quantities (negative allowed for returns)
3. Date ranges within expected bounds
4. Commodity names standardized (lowercase, trimmed)

### Key Principle
***"Silver is standardized, not analytical."***
It exists to make transformation easier, not to answer questions directly.