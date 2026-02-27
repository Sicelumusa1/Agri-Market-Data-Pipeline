{{ config(
    materialized='table',
    partition_by={
        'field': 'market_date',
        'data_type': 'date'
    },
    cluster_by=['commodity', 'market'],
    tags=['marts', 'daily']
) }}

WITH silver AS (
    SELECT * FROM {{ ref('int_silver_enriched') }}
    WHERE scrape_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
      AND is_return = FALSE  -- Exclude returns/corrections
      AND kg_sold > 0        -- Safeguard for price calculation
),

-- Calculate daily aggregates at variety level (Weighted Averages)
daily_variety_stats AS (
    SELECT
        scrape_date AS market_date,
        market,
        commodity,
        variety,
        container_name,
        COALESCE(grade, 'UNKNOWN') AS grade,
        size_value,
        color,
        
        -- Correct Weighted Price Calculation (volume-weighted to avoid skew)
        ROUND(SAFE_DIVIDE(SUM(value_sold), SUM(kg_sold)), 2) AS avg_price_per_kg,
        MAX(average_price_per_kg) AS max_price_achieved,
        MIN(average_price_per_kg) AS min_price_observed,
        
        -- Volume metrics
        SUM(kg_sold) AS total_kg_sold,
        SUM(value_sold) AS total_value_sold,
        COUNT(DISTINCT variety_id) AS variety_count,
        
        -- Container metrics
        AVG(unit_mass) AS avg_unit_mass,
        
        -- Market context (using MAX since these were joined attributes in Silver)
        MAX(total_market_kg) AS daily_market_volume,
        MAX(total_market_value) AS daily_market_value,
        
        -- Sample size for confidence
        COUNT(*) AS transaction_count
        
    FROM silver
    GROUP BY 1,2,3,4,5,6,7,8
),

-- Add rankings WITHIN commodity (across all varieties)
ranked_within_commodity AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY market_date, market, commodity 
            ORDER BY avg_price_per_kg DESC
        ) AS price_rank_within_commodity
    FROM daily_variety_stats
),

-- Add rankings WITHIN variety (across containers/grades)
ranked_within_variety AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (
            PARTITION BY market_date, market, commodity, variety
            ORDER BY avg_price_per_kg DESC
        ) AS price_rank_within_variety
    FROM ranked_within_commodity
),

-- Calculate historical averages for comparison
with_historical_context AS (
    SELECT 
        r.*,
        
        -- 7-day rolling weighted average price
        AVG(avg_price_per_kg) OVER (
            PARTITION BY market, commodity, variety, container_name, grade
            ORDER BY market_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS seven_day_avg_price,
        
        -- 30-day average volume
        AVG(total_kg_sold) OVER (
            PARTITION BY market, commodity, variety, container_name, grade
            ORDER BY market_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS thirty_day_avg_volume,
        
        -- Price volatility
        STDDEV(avg_price_per_kg) OVER (
            PARTITION BY market, commodity, variety, container_name, grade
            ORDER BY market_date
            ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
        ) AS price_volatility_30day
        
    FROM ranked_within_variety r
),

-- Container intelligence logic
container_scoring AS (
    SELECT 
        *,
        -- Composite score
        ROUND(
            (avg_price_per_kg * 0.5) + 
            ((avg_price_per_kg * avg_unit_mass) * 0.3) - 
            (COALESCE(price_volatility_30day, 0) * 0.2)
        , 2) AS container_score,
        
        -- Volume comparison
        CASE 
            WHEN thirty_day_avg_volume IS NULL OR thirty_day_avg_volume = 0 THEN 'Insufficient Data'
            WHEN total_kg_sold > thirty_day_avg_volume * 1.2 THEN 'Well Above Normal'
            WHEN total_kg_sold > thirty_day_avg_volume * 1.05 THEN 'Above Normal'
            WHEN total_kg_sold < thirty_day_avg_volume * 0.8 THEN 'Well Below Normal'
            WHEN total_kg_sold < thirty_day_avg_volume * 0.95 THEN 'Below Normal'
            ELSE 'Normal'
        END AS volume_comparison,
        
        SAFE_DIVIDE(total_kg_sold - thirty_day_avg_volume, thirty_day_avg_volume) * 100 AS volume_vs_historical_pct,
        
        -- Price stability indicator
        CASE 
            WHEN price_volatility_30day < 2 THEN 'Very Stable'
            WHEN price_volatility_30day < 5 THEN 'Stable'
            WHEN price_volatility_30day < 10 THEN 'Moderate'
            ELSE 'Volatile'
        END AS price_stability,
        
        -- Premium indicator - price > 20% above average
        avg_price_per_kg > 1.2 * AVG(avg_price_per_kg) OVER (
            PARTITION BY market_date, market, commodity
        ) AS is_premium
        
    FROM with_historical_context
),

-- Final Recommendations
final AS (
    SELECT 
        *,
        -- Recommendation logic
        CASE 
            WHEN container_score = MAX(container_score) OVER (PARTITION BY market_date, market, commodity, variety) THEN 'Recommended'
            WHEN container_score > 0.8 * MAX(container_score) OVER (PARTITION BY market_date, market, commodity, variety) THEN 'Consider'
            ELSE 'Avoid'
        END AS container_recommendation,
        
        -- Recommendation reason 
        CASE 
            WHEN avg_price_per_kg = MAX(avg_price_per_kg) OVER (PARTITION BY market_date, market, commodity, variety) 
                 AND price_volatility_30day < AVG(price_volatility_30day) OVER (PARTITION BY commodity) * 0.8 
                 THEN 'Best price with stable demand'
            WHEN avg_price_per_kg = MAX(avg_price_per_kg) OVER (PARTITION BY market_date, market, commodity, variety) 
                 THEN 'Highest price today'
            WHEN (avg_price_per_kg * avg_unit_mass) = MAX(avg_price_per_kg * avg_unit_mass) OVER (PARTITION BY market_date, market, commodity, variety) 
                 THEN 'Highest value per container'
            WHEN price_volatility_30day = MIN(price_volatility_30day) OVER (PARTITION BY market_date, market, commodity, variety) 
                 THEN 'Most stable pricing'
            ELSE 'Balanced option'
        END AS recommendation_reason,
        
        -- Data quality indicators
        CASE 
            WHEN transaction_count > 10 AND (price_volatility_30day < 5 OR price_volatility_30day IS NULL) THEN 'High'
            WHEN transaction_count > 5 OR price_volatility_30day < 10 THEN 'Medium'
            ELSE 'Low'
        END AS data_quality_flag
        
    FROM container_scoring
)

SELECT 
    market_date,
    market,
    commodity,
    variety,
    container_name AS container_type,
    grade,
    avg_price_per_kg,
    max_price_achieved,
    min_price_observed,
    total_kg_sold,
    total_value_sold,
    transaction_count,
    price_rank_within_commodity,
    price_rank_within_variety,
    container_score,
    container_recommendation,
    recommendation_reason,      
    volume_comparison,
    ROUND(volume_vs_historical_pct, 1) AS volume_vs_historical_pct,
    price_stability,            
    is_premium,                
    data_quality_flag,
    CURRENT_TIMESTAMP() AS dbt_loaded_at
FROM final
WHERE market_date >= '2020-01-01'
  AND market_date <= CURRENT_DATE()
