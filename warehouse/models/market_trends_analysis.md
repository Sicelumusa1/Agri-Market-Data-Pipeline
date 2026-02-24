# Model: `market_trends_analysis`

## Purpose
**Answers:** "Where is the market heading?"

This table provides strategic market intelligence for long-term planning, helping farmers decide what to plant next season and whether to invest in premium quality.

## Grain
**One row per:** `market_date` (daily market summary)

## Update Frequency
Daily (append new row)

## Table Structure

```sql
CREATE TABLE gold.market_trends_analysis (
    -- Time Dimensions
    market_date DATE,
    year INT64,
    month INT64,
    week_of_year INT64,
    
    -- Market Size Metrics
    total_market_volume FLOAT64,
    total_market_value FLOAT64,
    active_varieties INT64,
    active_containers INT64,
    
    -- Price Metrics
    market_avg_price FLOAT64,
    market_price_range FLOAT64,
    
    -- Premium Segment
    premium_segment_value FLOAT64,
    premium_percentage FLOAT64,
    
    -- Directional Indicators (Plain Language)
    volume_direction STRING,
    price_direction STRING,
    premium_direction STRING,
    market_condition STRING,
    
    -- Trend Metrics
    volume_change_pct FLOAT64,
    price_change_pct FLOAT64,
    seven_day_avg_price FLOAT64,
    thirty_day_avg_price FLOAT64,
    
    -- Market Intelligence
    diversity_index FLOAT64,
    forecast_confidence STRING
)
PARTITION BY market_date
CLUSTER BY year, month;
```

## Derived Metrics Explained

### Directional Indicators (Farmer-Friendly)
```sql
volume_direction = CASE 
    WHEN volume_change_pct > 10 THEN 'Growing'
    WHEN volume_change_pct < -10 THEN 'Declining'
    ELSE 'Stable ⚖️'
END

price_direction = CASE 
    WHEN price_change_pct > 5 THEN 'Increasing'
    WHEN price_change_pct < -5 THEN 'Decreasing'
    ELSE 'Stable ⚖️'
END

premium_direction = CASE 
    WHEN premium_percentage - LAG(premium_percentage, 30) > 5 THEN 'Expanding'
    WHEN premium_percentage - LAG(premium_percentage, 30) < -5 THEN 'Shrinking'
    ELSE 'Stable'
END
-- Farmers think in directions, not percentages
```

### Market Condition
```sql
market_condition = CASE 
    WHEN market_avg_price > 1.1 * three_month_avg THEN 'Hot Market'
    WHEN market_avg_price < 0.9 * three_month_avg THEN 'Cool Market'
    ELSE 'Stable Market'
END
```

### Diversity Index
```sql
diversity_index = 1 - SUM(POWER(market_share, 2))
-- 0 = monopoly (one variety dominates)
-- 1 = perfectly diverse (many equal varieties)
```

### Partitioning & Clustering

- Partitioned by: market_date (daily partitions)

- Clustered by: year, month (seasonal analysis)

## Typical Dashboard Queries

### "Is the apple market growing?"
```sql
SELECT market_date, total_market_volume, volume_direction
FROM gold.market_trends_analysis
WHERE commodity = 'apples'
ORDER BY market_date DESC
LIMIT 30
```

### "Is premium quality worth investing in?"
```sql
SELECT market_date, premium_percentage, premium_direction
FROM gold.market_trends_analysis
WHERE premium_direction = 'Expanding'
ORDER BY market_date DESC
```

### "What should I plant next season?"
```sql

SELECT year, variety, SUM(total_value) as value
FROM gold.market_trends_analysis
WHERE year = 2025
GROUP BY year, variety
ORDER BY value DESC
```

### Known Limitations

- Market-level only: Doesn't show individual performance

- No predictions: Shows trends, not forecasts

- Requires history: Meaningful trends need 90+ days

- External factors: Weather, economy not included

### Related Models

- Depends on: silver.silver_enriched_data (historical)

- Referenced by: Looker Studio "Strategic Planning" dashboard

- See also: product_optimization for specific products