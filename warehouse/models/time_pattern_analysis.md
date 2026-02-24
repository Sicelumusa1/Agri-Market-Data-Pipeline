# Model: `time_pattern_analysis`

## Purpose
**Answers:** "When should I sell?"

This table identifies optimal selling times by analyzing historical patterns across days of week, weeks of month, and seasons. Farmers use this to plan harvest and delivery schedules.

## Grain
**One row per:** `day_name` + `week_in_month` + `month_name` + `season`  
(Aggregated across all historical data)

## Update Frequency
Weekly (full refresh) + Daily incremental

## Table Structure

```sql
CREATE TABLE gold.time_pattern_analysis (
    -- Time Dimensions
    day_name STRING,
    week_in_month INT64,
    month_name STRING,
    season STRING,
    is_weekend BOOLEAN,
    is_month_end BOOLEAN,
    
    -- Price Patterns
    avg_price FLOAT64,
    median_price FLOAT64,
    min_price FLOAT64,
    max_price FLOAT64,
    price_volatility FLOAT64,
    
    -- Volume Patterns
    avg_daily_volume FLOAT64,
    
    -- Confidence & Ranges
    sample_size INT64,
    confidence_score STRING,
    price_lower_bound FLOAT64,
    price_upper_bound FLOAT64,
    
    -- Rankings
    day_price_rank INT64,
    price_premium_vs_avg FLOAT64
)
CLUSTER BY season, day_name;
```

## Derived Metrics Explained

### Confidence Bands

```sql
price_lower_bound = avg_price - (price_volatility * 1.96 / SQRT(sample_size))
price_upper_bound = avg_price + (price_volatility * 1.96 / SQRT(sample_size))

confidence_score = CASE 
    WHEN sample_size > 30 AND price_volatility < 0.2 THEN 'High'
    WHEN sample_size > 15 AND price_volatility < 0.3 THEN 'Medium'
    ELSE 'Low - Use with caution'
END
-- Shows farmers the range, not just a single number
```

### Day Price Rank
```sql
day_price_rank = ROW_NUMBER() OVER (
    PARTITION BY commodity 
    ORDER BY avg_price DESC
)
-- 1 = Best day to sell for this commodity
```

### Partitioning & Clustering
- Not partitioned (small table, always fully scanned)

- Clustered by: season, day_name (common filters)

## Typical Dashboard Queries

### "What's the best day to sell apples?"
```sql
SELECT day_name, avg_price, confidence_score
FROM gold.time_pattern_analysis
WHERE commodity = 'apples'
ORDER BY day_price_rank
LIMIT 3
```

### "Is week 3 better than week 1?"
```sql
SELECT week_in_month, avg_price, price_lower_bound, price_upper_bound
FROM gold.time_pattern_analysis
WHERE commodity = 'apples'
  AND day_name = 'Tuesday'
ORDER BY week_in_month
```

### "Should I sell in summer or winter?"
```sql
SELECT season, avg_price, avg_daily_volume
FROM gold.time_pattern_analysis
WHERE commodity = 'apples'
GROUP BY season, avg_price, avg_daily_volume
ORDER BY avg_price DESC
```


### Known Limitations

- Requires sufficient history: Low confidence until 30+ days

- No causal analysis: Correlation ≠ causation

- Market-wide: Individual farmer timing may differ

- Static patterns: Assumes historical patterns continue


### Related Models

- Depends on: silver.silver_enriched_data (historical)

- Referenced by: Looker Studio "Planning Calendar" dashboard

- See also: daily_market_snapshot for today's context