
{{ config(
    materialized='table',
    cluster_by=['season', 'day_name'],
    tags=['marts', 'weekly']
) }}

WITH silver AS (
    SELECT * FROM {{ ref('int_silver_enriched') }}
    WHERE scrape_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        AND is_return = FALSE  -- Exclude returns from price pattern analysis
        AND kg_sold > 0 
),

-- Daily aggregates (Aggregating to the day level first)
daily_aggregates AS (
    SELECT
        scrape_date,
        commodity,
        day_of_week_num,
        day_name,
        week_in_month,
        season,
        -- Use SUMs here to allow for weighted averages later
        SUM(kg_sold) AS daily_kg,
        SUM(value_sold) AS daily_value,
        -- Calculate daily price for median/volatility distribution
        SAFE_DIVIDE(SUM(value_sold), SUM(kg_sold)) AS daily_avg_price
    FROM silver
    GROUP BY 1,2,3,4,5,6
),

-- Day of Week Patterns
day_of_week_patterns AS (
    SELECT
        'day_of_week' AS pattern_type,
        commodity,
        day_name,
        day_of_week_num,
        CAST(NULL AS INT64) AS week_in_month,
        CAST(NULL AS STRING) AS season,
        
        -- Correct Weighted Average
        ROUND(SAFE_DIVIDE(SUM(daily_value), SUM(daily_kg)), 2) AS avg_price,
        -- BigQuery Median Fix
        ROUND(APPROX_QUANTILES(daily_avg_price, 2)[OFFSET(1)], 2) AS median_price,
        ROUND(MIN(daily_avg_price), 2) AS min_price,
        ROUND(MAX(daily_avg_price), 2) AS max_price,
        ROUND(STDDEV(daily_avg_price), 2) AS price_volatility,
        ROUND(AVG(daily_kg), 0) AS avg_daily_volume,
        COUNT(*) AS sample_size,
        
        -- Confidence Intervals
        ROUND(AVG(daily_avg_price) - (1.96 * STDDEV(daily_avg_price) / SQRT(NULLIF(COUNT(*), 0))), 2) AS price_lower_bound,
        ROUND(AVG(daily_avg_price) + (1.96 * STDDEV(daily_avg_price) / SQRT(NULLIF(COUNT(*), 0))), 2) AS price_upper_bound,
        
        ROW_NUMBER() OVER (PARTITION BY commodity ORDER BY SAFE_DIVIDE(SUM(daily_value), SUM(daily_kg)) DESC) AS price_rank
    FROM daily_aggregates
    GROUP BY commodity, day_name, day_of_week_num
),

-- Week in Month Patterns
week_in_month_patterns AS (
    SELECT
        'week_in_month' AS pattern_type,
        commodity,
        CAST(NULL AS STRING) AS day_name,
        CAST(NULL AS INT64) AS day_of_week_num,
        week_in_month,
        CAST(NULL AS STRING) AS season,
        
        ROUND(SAFE_DIVIDE(SUM(daily_value), SUM(daily_kg)), 2) AS avg_price,
        ROUND(APPROX_QUANTILES(daily_avg_price, 2)[OFFSET(1)], 2) AS median_price,
        ROUND(MIN(daily_avg_price), 2) AS min_price,
        ROUND(MAX(daily_avg_price), 2) AS max_price,
        ROUND(STDDEV(daily_avg_price), 2) AS price_volatility,
        ROUND(AVG(daily_kg), 0) AS avg_daily_volume,
        COUNT(*) AS sample_size,
        
        ROUND(AVG(daily_avg_price) - (1.96 * STDDEV(daily_avg_price) / SQRT(NULLIF(COUNT(*), 0))), 2) AS price_lower_bound,
        ROUND(AVG(daily_avg_price) + (1.96 * STDDEV(daily_avg_price) / SQRT(NULLIF(COUNT(*), 0))), 2) AS price_upper_bound,
        
        ROW_NUMBER() OVER (PARTITION BY commodity ORDER BY SAFE_DIVIDE(SUM(daily_value), SUM(daily_kg)) DESC) AS price_rank
    FROM daily_aggregates
    GROUP BY commodity, week_in_month
),

-- Season Patterns
season_patterns AS (
    SELECT
        'season' AS pattern_type,
        commodity,
        CAST(NULL AS STRING) AS day_name,
        CAST(NULL AS INT64) AS day_of_week_num,
        CAST(NULL AS INT64) AS week_in_month,
        season,
        
        ROUND(SAFE_DIVIDE(SUM(daily_value), SUM(daily_kg)), 2) AS avg_price,
        ROUND(APPROX_QUANTILES(daily_avg_price, 2)[OFFSET(1)], 2) AS median_price,
        ROUND(MIN(daily_avg_price), 2) AS min_price,
        ROUND(MAX(daily_avg_price), 2) AS max_price,
        ROUND(STDDEV(daily_avg_price), 2) AS price_volatility,
        ROUND(AVG(daily_kg), 0) AS avg_daily_volume,
        COUNT(*) AS sample_size,
        
        ROUND(AVG(daily_avg_price) - (1.96 * STDDEV(daily_avg_price) / SQRT(NULLIF(COUNT(*), 0))), 2) AS price_lower_bound,
        ROUND(AVG(daily_avg_price) + (1.96 * STDDEV(daily_avg_price) / SQRT(NULLIF(COUNT(*), 0))), 2) AS price_upper_bound,
        
        ROW_NUMBER() OVER (PARTITION BY commodity ORDER BY SAFE_DIVIDE(SUM(daily_value), SUM(daily_kg)) DESC) AS price_rank
    FROM daily_aggregates
    GROUP BY commodity, season
),

all_patterns AS (
    SELECT * FROM day_of_week_patterns
    UNION ALL
    SELECT * FROM week_in_month_patterns
    UNION ALL
    SELECT * FROM season_patterns
),

final AS (
    SELECT
        *,
        CASE 
            WHEN sample_size >= 30 AND price_volatility < 5 THEN 'High'
            WHEN sample_size >= 15 AND price_volatility < 10 THEN 'Medium'
            ELSE 'Low'
        END AS confidence_score,
        
        ROUND(avg_price - AVG(avg_price) OVER (PARTITION BY commodity), 2) AS price_premium_vs_avg,
        CURRENT_DATE() AS analysis_date
    FROM all_patterns
)

SELECT * FROM final
