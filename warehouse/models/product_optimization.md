# Model: `product_optimization`

## Purpose
**Answers:** "What configuration should I pack?"

This table analyzes which product combinations (variety + container + size + grade) perform best, helping farmers optimize packaging decisions for maximum profit.

## Grain
**One row per:** `variety` + `container_type` + `size_category` + `grade`  
(Aggregated across all historical data)

## Update Frequency
Weekly (full refresh)

## Table Structure

```sql
CREATE TABLE gold.product_optimization (
    -- Product Dimensions
    variety STRING,
    container_type STRING,
    size_category STRING,
    grade STRING,
    
    -- Performance Metrics
    avg_price_per_kg FLOAT64,
    avg_value_per_container FLOAT64,
    total_kg_sold FLOAT64,
    market_share_percent FLOAT64,
    days_sold INT64,
    
    -- Rankings (explicit scope)
    rank_by_price INT64,
    rank_by_volume INT64,
    rank_by_value INT64,
    overall_rank INT64,
    
    -- Intelligence Metrics
    optimization_score FLOAT64,
    price_stability FLOAT64,
    volume_trend FLOAT64,
    
    -- Metadata
    last_observed DATE,
    sample_size INT64
)
CLUSTER BY variety, grade;
```

## Derived Metrics Explained

### Optimization Score
```sql
optimization_score = (
    avg_price_per_kg * LOG(total_kg_sold + 1) / 100
)
-- Balances price (premium) with volume (practicality)
-- High price with tiny volume = low score (not useful)
-- Good price with good volume = high score (sweet spot)
```

### Multiple Rankings
```sql
rank_by_price = ROW_NUMBER() OVER (ORDER BY avg_price_per_kg DESC)
rank_by_volume = ROW_NUMBER() OVER (ORDER BY total_kg_sold DESC)
rank_by_value = ROW_NUMBER() OVER (ORDER BY avg_value_per_container DESC)
overall_rank = ROW_NUMBER() OVER (ORDER BY optimization_score DESC)
-- Farmers can see WHY something is recommended
```

### Volume Trend
```sql
volume_trend = (
    recent_volume - previous_volume
) / NULLIF(previous_volume, 0) * 100
-- Positive = growing demand, negative = shrinking
```

### Partitioning & Clustering

- Not partitioned (reference table, fully scanned)

- Clustered by: variety, grade (common filters)

## Typical Dashboard Queries

### "What's the best overall product combination?"
```sql
SELECT variety, container_type, size_category, grade, 
       optimization_score, avg_price_per_kg
FROM gold.product_optimization
WHERE overall_rank <= 5
ORDER BY overall_rank
```

### "Should I pack Class 1 or Class 2?"
```sql
SELECT grade, avg_price_per_kg, market_share_percent
FROM gold.product_optimization
WHERE variety = 'GRANNY SMITH'
  AND container_type = '18.5KG CARTON'
  AND size_category = 'Large'
ORDER BY grade
```

### "Is demand for this variety growing?"
```sql
SELECT variety, volume_trend, avg_price_per_kg
FROM gold.product_optimization
WHERE volume_trend > 10  -- Growing >10%
ORDER BY volume_trend DESC
```

### Known Limitations

- No causal analysis: Correlation ≠ causation

- Market-wide: Individual farm quality may differ

- Static until refresh: Updated weekly only

- Requires sufficient data: Low confidence for rare combinations

### Related Models

- Depends on: silver.silver_enriched_data (historical)

- Referenced by: Looker Studio "Product Strategy" dashboard

- See also: market_trends_analysis for category trends