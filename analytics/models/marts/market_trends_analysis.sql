{{ config(
    materialized='table',
    partition_by={'field': 'market_date', 'data_type': 'date'},
    cluster_by=['commodity', 'market'],
    tags=['marts', 'daily']
) }}

WITH silver AS (
    SELECT * FROM {{ ref('int_silver_enriched') }}
    WHERE scrape_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 450 DAY) -- Buffer for YoY
      AND is_return = FALSE
      AND kg_sold > 0
),

-- Step 1: Daily market aggregates
daily_market_base AS (
    SELECT
        scrape_date AS market_date,
        market,
        commodity,
        UNIX_DATE(scrape_date) AS date_unix,
        SUM(kg_sold) AS total_volume,
        SUM(value_sold) AS total_value,
        COUNT(DISTINCT variety) AS active_varieties,
        SAFE_DIVIDE(SUM(value_sold), SUM(kg_sold)) AS daily_avg_price,
        MAX(average_price_per_kg) AS max_price,
        MIN(average_price_per_kg) AS min_price
    FROM silver
    GROUP BY 1,2,3,4
),

-- Step 2: Premium segment calculation (Safely separated)
daily_premium AS (
    SELECT
        s.scrape_date AS market_date, s.market, s.commodity,
        SUM(CASE WHEN s.average_price_per_kg > 1.3 * d.daily_avg_price THEN s.value_sold ELSE 0 END) AS premium_value
    FROM silver s
    INNER JOIN daily_market_base d ON s.scrape_date = d.market_date AND s.market = d.market AND s.commodity = d.commodity
    GROUP BY 1,2,3
),

-- Step 3: Base + Premium
daily_market AS (
    SELECT d.*, COALESCE(p.premium_value, 0) AS premium_value FROM daily_market_base d
    LEFT JOIN daily_premium p ON d.market_date = p.market_date AND d.market = p.market AND d.commodity = p.commodity
),

-- Step 4: Rolling Windows (The Data Engineering Foundation)
with_rolling AS (
    SELECT 
        *,
        -- 7-day and 30-day Volume Averages
        AVG(total_volume) OVER (PARTITION BY market, commodity ORDER BY date_unix RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS vol_7d_avg,
        AVG(total_volume) OVER (PARTITION BY market, commodity ORDER BY date_unix RANGE BETWEEN 29 PRECEDING AND CURRENT ROW) AS vol_30d_avg,
        -- 7-day and 30-day Price Averages
        AVG(daily_avg_price) OVER (PARTITION BY market, commodity ORDER BY date_unix RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS price_7d_avg,
        AVG(daily_avg_price) OVER (PARTITION BY market, commodity ORDER BY date_unix RANGE BETWEEN 29 PRECEDING AND CURRENT ROW) AS price_30d_avg,
        -- Volatility
        STDDEV(daily_avg_price) OVER (PARTITION BY market, commodity ORDER BY date_unix RANGE BETWEEN 29 PRECEDING AND CURRENT ROW) AS price_vol_30d,
        -- Data Density
        COUNT(*) OVER (PARTITION BY market, commodity ORDER BY date_unix RANGE BETWEEN 6 PRECEDING AND CURRENT ROW) AS days_in_7d
    FROM daily_market
),

-- Step 5: Year-over-Year (YoY) and Week-over-Week (WoW) joins
with_trends_raw AS (
    SELECT 
        curr.*,
        -- WoW (7 days ago)
        prev_w.total_volume AS vol_last_week,
        prev_w.daily_avg_price AS price_last_week,
        -- YoY (364 days ago)
        prev_y.total_volume AS vol_last_year,
        prev_y.daily_avg_price AS price_last_year
    FROM with_rolling curr
    LEFT JOIN with_rolling prev_w ON curr.market = prev_w.market AND curr.commodity = prev_w.commodity AND curr.market_date = DATE_ADD(prev_w.market_date, INTERVAL 7 DAY)
    LEFT JOIN with_rolling prev_y ON curr.market = prev_y.market AND curr.commodity = prev_y.commodity AND curr.market_date = DATE_ADD(prev_y.market_date, INTERVAL 52 WEEK)
),

-- Step 6: Percentage Changes
with_pct AS (
    SELECT 
        *,
        ROUND(SAFE_DIVIDE(total_volume - vol_last_week, vol_last_week) * 100, 1) AS volume_change_wow_pct,
        ROUND(SAFE_DIVIDE(daily_avg_price - price_last_week, price_last_week) * 100, 1) AS price_change_wow_pct,
        ROUND(SAFE_DIVIDE(total_volume - vol_last_year, vol_last_year) * 100, 1) AS volume_change_yoy_pct,
        ROUND(SAFE_DIVIDE(daily_avg_price - price_last_year, price_last_year) * 100, 1) AS price_change_yoy_pct
    FROM with_trends_raw
),

-- Step 7: Farmer-Specific Intelligence (The "Value" Layer)
final_intel AS (
    SELECT 
        *,
        -- 1. Volume Trend Direction
        CASE 
            WHEN vol_7d_avg > vol_30d_avg * 1.10 THEN 'Surging Demand'
            WHEN vol_7d_avg > vol_30d_avg * 1.02 THEN 'Rising'
            WHEN vol_7d_avg < vol_30d_avg * 0.90 THEN 'Falling Demand'
            ELSE 'Stable'
        END AS volume_trend_direction,

        -- 2. Price Trend Direction
        CASE 
            WHEN price_7d_avg > price_30d_avg * 1.05 THEN 'Rising Prices'
            WHEN price_7d_avg < price_30d_avg * 0.95 THEN 'Dropping Prices'
            ELSE 'Stable'
        END AS price_trend_direction,

        -- 3. Market Health Score (0-100)
        -- Logic: High price stability (25) + Positive WoW Price (25) + Variety diversity (25) + Premium % (25)
        ROUND(
            (IF(price_vol_30d < 3, 25, IF(price_vol_30d < 7, 15, 5))) +
            (IF(price_change_wow_pct > 0, 25, 10)) +
            (IF(active_varieties > 5, 25, 10)) +
            (IF(SAFE_DIVIDE(premium_value, total_value) > 0.2, 25, 10)),
        0) AS market_health_score
    FROM with_pct
)

-- Final SELECT with Opportunities & Risks
SELECT 
    market_date, market, commodity,
    total_volume, total_value, 
    ROUND(daily_avg_price, 2) AS avg_price_per_kg,
    ROUND(premium_value, 2) AS premium_value,
    active_varieties,
    
    -- Farmer Trends
    volume_change_wow_pct, price_change_wow_pct,
    volume_change_yoy_pct, price_change_yoy_pct,
    volume_trend_direction, price_trend_direction,
    
    -- Market Health
    market_health_score,
    CASE 
        WHEN market_health_score >= 80 THEN 'Booming'
        WHEN market_health_score >= 60 THEN 'Growing'
        WHEN market_health_score >= 40 THEN 'Stable'
        WHEN market_health_score >= 25 THEN 'Slowing'
        ELSE 'Declining'
    END AS market_condition,

    -- Risk Metrics
    ROUND(price_vol_30d, 2) AS price_volatility,
    ROUND(SAFE_DIVIDE(premium_value, total_value) * 100, 1) AS premium_percentage,

    -- Opportunity Indicators
    (price_trend_direction = 'Rising Prices' AND volume_trend_direction = 'Surging Demand') AS is_hot_opportunity,
    (price_vol_30d > 10 OR market_health_score < 30) AS is_high_risk,

    -- Metadata
    days_in_7d AS data_confidence_score,
    CURRENT_DATE() AS analysis_date
FROM final_intel
WHERE market_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
-- ORDER BY market_date DESC, market_health_score DESC