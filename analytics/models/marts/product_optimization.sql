{{ config(
    materialized='table',
    partition_by={
        'field': 'analysis_date',
        'data_type': 'date'
    },
    cluster_by=['variety', 'grade'],
    tags=['marts', 'weekly']
) }}

WITH silver AS (
    SELECT * FROM {{ ref('int_silver_enriched') }}
    WHERE scrape_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
      AND is_return = FALSE
      AND kg_sold > 0
),

-- Daily product aggregates
daily_product_stats AS (
    SELECT
        scrape_date,
        commodity,
        variety,
        container_name AS container_type,
        grade,
        CASE 
            WHEN size_value IN ('S', 'M', 'L', 'XL', 'XXL') THEN size_value
            WHEN REGEXP_CONTAINS(size_value, r'^[0-9]+$') THEN
                CASE 
                    WHEN CAST(size_value AS INT64) <= 10 THEN 'Extra Large'
                    WHEN CAST(size_value AS INT64) <= 25 THEN 'Large'
                    WHEN CAST(size_value AS INT64) <= 50 THEN 'Medium'
                    ELSE 'Small'
                END
            ELSE 'Unclassified'
        END AS size_category,
        SUM(kg_sold) AS daily_kg,
        SUM(value_sold) AS daily_value,
        SUM(qty_sold) AS daily_units,
        COUNT(*) AS daily_transactions,
        SAFE_DIVIDE(SUM(value_sold), SUM(kg_sold)) AS daily_avg_price_per_kg
    FROM silver
    GROUP BY 1, 2, 3, 4, 5, 6
),

-- Calculate product totals first (without volatility)
product_totals AS (
    SELECT
        commodity,
        variety,
        container_type,
        size_category,
        grade,
        SUM(daily_kg) AS total_kg_sold,
        SUM(daily_value) AS total_value_sold,
        SUM(daily_units) AS total_units_sold,
        SUM(daily_transactions) AS total_transactions,
        COUNT(DISTINCT scrape_date) AS days_sold,
        AVG(daily_kg) AS avg_daily_volume,
        STDDEV(daily_kg) AS volume_volatility,
        SAFE_DIVIDE(SUM(daily_value), SUM(daily_kg)) AS weighted_avg_price,
        SAFE_DIVIDE(SUM(daily_value), SUM(daily_units)) AS avg_price_per_unit,
        
        -- Recent and previous volume for trend
        SUM(CASE WHEN scrape_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) THEN daily_kg END) AS recent_volume,
        SUM(CASE WHEN scrape_date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY) AND DATE_SUB(CURRENT_DATE(), INTERVAL 31 DAY) THEN daily_kg END) AS previous_volume
        
    FROM daily_product_stats
    GROUP BY 1, 2, 3, 4, 5
),

-- Calculate price volatility separately (needs daily values)
price_volatility AS (
    SELECT
        d.commodity,
        d.variety,
        d.container_type,
        d.size_category,
        d.grade,
        -- Weighted standard deviation formula
        SQRT(
            SUM(d.daily_kg * POW(d.daily_avg_price_per_kg - t.weighted_avg_price, 2)) 
            / SUM(d.daily_kg)
        ) AS price_volatility
    FROM daily_product_stats d
    INNER JOIN product_totals t
        ON d.commodity = t.commodity
        AND d.variety = t.variety
        AND d.container_type = t.container_type
        AND d.size_category = t.size_category
        AND d.grade = t.grade
    GROUP BY 1, 2, 3, 4, 5
),

-- Combine everything
product_combined AS (
    SELECT 
        t.*,
        pv.price_volatility,
        
        -- Market share using window function
        SAFE_DIVIDE(t.total_value_sold, SUM(t.total_value_sold) OVER (PARTITION BY t.commodity)) * 100 AS market_share_percent,
        
        -- Value per container
        ROUND(t.weighted_avg_price * (t.total_kg_sold / NULLIF(t.total_units_sold, 0)), 2) AS avg_value_per_container,
        
        -- Trends
        SAFE_DIVIDE(t.recent_volume - t.previous_volume, t.previous_volume) * 100 AS volume_trend_pct,
        
        -- Optimization score
        (t.weighted_avg_price * LOG(t.total_kg_sold + 1)) / 1000 AS optimization_score
        
    FROM product_totals t
    LEFT JOIN price_volatility pv
        ON t.commodity = pv.commodity
        AND t.variety = pv.variety
        AND t.container_type = pv.container_type
        AND t.size_category = pv.size_category
        AND t.grade = pv.grade
),

-- Add derived metrics
with_metrics AS (
    SELECT 
        *,
        ROUND(weighted_avg_price, 2) AS avg_price_per_kg,
        ROUND(avg_price_per_unit, 2) AS avg_price_per_unit_display,
        ROUND(avg_value_per_container, 2) AS avg_value_per_container_display,
        ROUND(optimization_score, 2) AS optimization_score_display,
        ROUND(price_volatility, 2) AS price_volatility_display,
        
        CASE 
            WHEN price_volatility < 2 THEN 'Very Stable'
            WHEN price_volatility < 5 THEN 'Stable'
            WHEN price_volatility < 10 THEN 'Moderate'
            ELSE 'Volatile'
        END AS price_stability,
        
        CASE 
            WHEN volume_volatility / NULLIF(avg_daily_volume, 0) < 0.3 THEN 'Very Consistent'
            WHEN volume_volatility / NULLIF(avg_daily_volume, 0) < 0.6 THEN 'Consistent'
            WHEN volume_volatility / NULLIF(avg_daily_volume, 0) < 1.0 THEN 'Variable'
            ELSE 'Highly Variable'
        END AS volume_consistency
        
    FROM product_combined
),

-- Rankings and metadata
with_rankings AS (
    SELECT 
        *,
        ROW_NUMBER() OVER (ORDER BY optimization_score DESC) AS overall_rank,
        ROW_NUMBER() OVER (ORDER BY weighted_avg_price DESC) AS rank_by_price,
        ROW_NUMBER() OVER (ORDER BY total_kg_sold DESC) AS rank_by_volume,
        ROW_NUMBER() OVER (ORDER BY avg_value_per_container DESC) AS rank_by_value,
        CURRENT_DATE() AS analysis_date,
        'Last 90 days' AS analysis_period
    FROM with_metrics
    WHERE total_kg_sold > 0
)

-- Final Select
SELECT 
    commodity, 
    variety, 
    container_type, 
    size_category, 
    grade,
    
    -- Price metrics
    ROUND(weighted_avg_price, 2) AS avg_price_per_kg,
    ROUND(avg_price_per_unit, 2) AS avg_price_per_unit,
    ROUND(avg_value_per_container, 2) AS avg_value_per_container,
    
    -- Volume metrics
    ROUND(total_kg_sold, 2) AS total_kg_sold,
    ROUND(total_value_sold, 2) AS total_value_sold,
    total_units_sold,
    days_sold,
    total_transactions,
    ROUND(avg_daily_volume, 2) AS avg_daily_volume,
    ROUND(market_share_percent, 2) AS market_share_percent,
    
    -- Intelligence metrics
    ROUND(optimization_score, 2) AS optimization_score,
    price_stability,
    volume_consistency,
    ROUND(volume_trend_pct, 1) AS volume_trend_pct,
    
    -- Rankings
    rank_by_price,
    rank_by_volume,
    rank_by_value,
    overall_rank,
    
    -- Performance tiers
    CASE 
        WHEN overall_rank <= 10 THEN 'Top Performer'
        WHEN overall_rank <= 25 THEN 'Strong Performer'
        WHEN overall_rank <= 50 THEN 'Average Performer'
        ELSE 'Low Performer'
    END AS performance_tier,
    
    -- Metadata
    analysis_date,
    analysis_period
    
FROM with_rankings
-- ORDER BY overall_rank