# Model: `daily_market_snapshot`

## Purpose
**Answers:** "What should I sell today?"

This table provides farmers with a real-time snapshot of today's market conditions, enabling immediate tactical decisions about which varieties and containers to prioritize.

## Grain
**One row per:** `market_date` + `commodity` + `variety` + `container_type` + `grade`

## Update Frequency
Daily at 4 PM (after silver layer refresh)

## Table Structure
```sql
CREATE TABLE gold.daily_market_snapshot (
    -- Dimensions (for filtering/grouping)
    market_date DATE,
    commodity STRING,
    variety STRING,
    container_type STRING,
    grade STRING,
    
    -- Facts (the numbers)
    avg_price_per_kg FLOAT64,
    max_price_achieved FLOAT64,
    min_price_observed FLOAT64,
    total_kg_sold FLOAT64,
    total_value_sold FLOAT64,
    transaction_count INT64,
    
    -- Price Rankings (explicit scope)
    price_rank_within_commodity INT64,
    price_rank_within_variety INT64,
    
    -- Container Recommendations
    container_score FLOAT64,
    container_recommendation STRING,
    recommendation_reason STRING,
    
    -- Volume Context
    volume_comparison STRING,
    volume_vs_historical_pct FLOAT64
)
PARTITION BY market_date
CLUSTER BY commodity, variety;
```
## Derived Metrics Explained

### Price Rankings
```sql
price_rank_within_commodity = ROW_NUMBER() OVER (
    PARTITION BY market_date, commodity 
    ORDER BY avg_price_per_kg DESC
)
-- Tells farmer: `This is the #1 most expensive apple variety today`
```
### Container Score (Composite)
```sql
container_score = (
    avg_price_per_kg * 0.5 +      -- Price matters most
    avg_value_per_container * 0.3 + -- Total value important
    (1 - price_volatility) * 0.2    -- Stability matters
)
-- Balances multiple factors for better recommendations
```
### Container Recommendation
```sql
container_recommendation = CASE 
    WHEN container_score = MAX(container_score) OVER (
        PARTITION BY market_date, commodity, variety
    ) THEN 'Recommended'
    WHEN container_score > 0.7 * MAX(container_score) OVER (
        PARTITION BY market_date, commodity, variety
    ) THEN 'Consider'
    ELSE 'Avoid'
END
```
### Volume Context
```sql
volume_comparison = CASE 
    WHEN volume_vs_historical_pct > 20 THEN 'Well Above Normal'
    WHEN volume_vs_historical_pct > 5 THEN 'Above Normal'
    WHEN volume_vs_historical_pct < -20 THEN 'Well Below Normal'
    WHEN volume_vs_historical_pct < -5 THEN 'Below Normal'
    ELSE 'Normal'
END
-- Farmers understand `Above Normal" better than "75th percentile`
```
### Partitioning & Clustering

***Partitioned by***: market_date (daily partitions)

    Queries for "today" scan 1 partition = fast + cheap

***Clustered by***: commodity, variety

    Farmers always filter by apple type first

## Typical Dashboard Queries

### "What's the best variety to sell today?"
```sql
SELECT variety, avg_price_per_kg, container_recommendation
FROM gold.daily_market_snapshot
WHERE market_date = CURRENT_DATE()
  AND commodity = 'apples'
  AND price_rank_within_commodity <= 3
ORDER BY price_rank_within_commodity
```

### "Should I use the 18.5KG carton today?"
```sql
SELECT container_recommendation, recommendation_reason
FROM gold.daily_market_snapshot
WHERE market_date = CURRENT_DATE()
  AND commodity = 'apples'
  AND variety = 'GRANNY SMITH'
  AND container_type = '18.5KG CARTON'
```

### "How busy is market today?"
```sql
SELECT *
FROM gold.daily_market_snapshot
WHERE market_date = CURRENT_DATE()
  AND commodity = 'apples'
LIMIT 1
```

## Known Limitations

- Single-day focus: For trends, use time_pattern_analysis

- No forecasts: This shows today only, not predictions

- Market-wide: Doesn't show individual farmer performance

- Requires historical data: Volume comparisons need 30+ days of history


## Related Models

- Depends on: silver.silver_enriched_data

- Referenced by: Looker Studio "Today's Market" dashboard

- See also: time_pattern_analysis for trends
