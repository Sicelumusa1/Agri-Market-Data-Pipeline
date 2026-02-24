# Partitioning & Clustering Strategy

## Overview
This document defines our partitioning and clustering strategy for BigQuery tables, optimizing for both query performance and cost efficiency.

## Design Philosophy
1. **Partition by most common filter**: Date is always filtered
2. **Cluster by next most common**: Commodity, variety
3. **Reference tables not partitioned**: Small tables scanned fully
4. **Balance performance vs cost**: Scan less data = lower cost

## Partitioning Strategy

### Why Date Partitioning?
| **Reason** | **Impact** |
|-----------|-----------|
| Most common filter | "Show me today's data" |
| Time-series analysis | Trends over time |
| BigQuery optimization | $5/TB scanned, partitions reduce scans |
| Data retention | Easy to expire old partitions |

### Partitioned Tables
| **Table** | **Partition Column** | **Partition Type** | **Why** |
|----------|---------------------|-------------------|---------|
| silver.silver_enriched_data | scrape_date | Daily | Raw data always filtered by date |
| gold.daily_market_snapshot | market_date | Daily | "Today's market" queries |
| gold.market_trends_analysis | market_date | Daily | Time-series analysis |

### Non-Partitioned Tables
| **Table** | **Why Not Partitioned** |
|----------|------------------------|
| gold.time_pattern_analysis | Small (<1,000 rows), always fully scanned |
| gold.product_optimization | Reference data, fully scanned once |

## Clustering Strategy

### Why Clustering?
- Organizes data within partitions
- Improves filter and aggregate performance
- No additional cost
- Up to 4 columns per table

### Clustering by Table

| **Table** | **Cluster Columns** | **Why These** |
|----------|--------------------|---------------|
| silver.silver_enriched_data | commodity, link_type | Filter by apple type + file source |
| gold.daily_market_snapshot | commodity, variety | Farmers always filter by apple type |
| gold.time_pattern_analysis | season, day_name | Common time-based filters |
| gold.product_optimization | variety, grade | Product-focused analysis |
| gold.market_trends_analysis | year, month | Seasonal trend analysis |

## Query Pattern Optimization

### Example 1: Farmer asks "What's best today?"
```sql
-- Without partitioning: Scans ALL historical data
SELECT * FROM gold.daily_market_snapshot
WHERE market_date = CURRENT_DATE()

-- With partitioning: Scans 1 day = 1/365th the data
-- Cost: 0.3% of full scan
```
### Example 2: "Show me Granny Smith prices"
```sql

-- Without clustering: Scans entire partition
-- With clustering: Scans only Granny Smith blocks
-- Improvement: 60-80% less data scanned
```
### Example 3: "Compare Tuesdays across seasons"
```sql

-- Clustering on season, day_name
-- Reads only relevant blocks, not entire table
-- Improvement: 40-60% less data
```

### Cost Impact Analysis
|Query Type |	Without Optimization    |	With Optimization   |	Savings |
|------------|--------------------------|-----------------------|-----------|
|Daily dashboard    |	365 GB/month    |	1 GB/month  |	99.7%   |
|Variety analysis   |	100 MB/query    |	20 MB/query |	80% |
|Seasonal patterns  |	50 MB/query |	20 MB/query |	60% |

## Maintenance Considerations

### Partition Expiration
```sql
-- Automatically expire old partitions
ALTER TABLE silver.silver_enriched_data
SET OPTIONS (
  partition_expiration_days = 365
);
-- Keeps costs contained
```
### Clustering Updates

- Clustering is automatic on write

- No manual maintenance needed

- Benefits improve over time

## Monitoring

### Query Performance
```sql

-- Check bytes processed
SELECT 
  job_id,
  total_bytes_processed / 1e9 as GB_processed,
  query
FROM `region-us`.INFORMATION_SCHEMA.JOBS
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)
ORDER BY total_bytes_processed DESC
```

### Partition Usage
```sql

-- See which partitions are accessed most
SELECT 
  DATE(creation_time) as date,
  SUM(total_bytes_processed) as bytes_processed
FROM `region-us`.INFORMATION_SCHEMA.JOBS
GROUP BY 1
ORDER BY 1 DESC
```

## Key Principle

- `"Partition by date, cluster by question."`
- Date is universal; clustering optimizes for specific analytical patterns.