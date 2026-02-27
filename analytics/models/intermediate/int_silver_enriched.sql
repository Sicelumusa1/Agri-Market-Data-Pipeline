-- joins staging tables to create the enriched silver layer.

{{ config(
    materialized='table',
    partition_by={
        'field': 'scrape_date',
        'data_type': 'date'
    },
    cluster_by=['market', 'commodity']
) }}

WITH variety AS (
    SELECT * FROM {{ ref('stg_market_variety') }}
),

container AS (
    SELECT 
        scrape_date, market, commodity, container_name,
        average_price_per_kg AS container_avg_price_per_kg,
        kg_sold AS container_kg_sold
    FROM {{ ref('stg_market_container') }}
),

summary AS (
    SELECT 
        scrape_date, market, commodity,
        kg_sold AS total_market_kg,
        value_sold AS total_market_value
    FROM {{ ref('stg_market_summary') }}
),

enriched AS (
    SELECT 
        v.*,
        -- Add date dimensions via macro
        {{ date_dimensions('v.scrape_date') | indent(8) }},

        -- If value or qty is negative, it's a return/correction
        CASE 
            WHEN v.value_sold < 0 OR v.qty_sold < 0 THEN TRUE 
            ELSE FALSE 
        END AS is_return,
        
        -- Bring in reference metrics
        c.container_avg_price_per_kg,
        s.total_market_kg,
        s.total_market_value,
        
        -- Price Comparisons
        ROUND(v.average_price_per_kg - c.container_avg_price_per_kg, 2) AS price_vs_container_avg,
        ROUND(v.average_price_per_kg - SAFE_DIVIDE(s.total_market_value, s.total_market_kg), 2) AS price_vs_market_avg
        
    FROM variety v
    LEFT JOIN container c 
        ON v.scrape_date = c.scrape_date
        AND v.market = c.market
        AND v.commodity = c.commodity
        AND v.container_name = c.container_name
    LEFT JOIN summary s 
        ON v.scrape_date = s.scrape_date
        AND v.market = s.market
        AND v.commodity = s.commodity
)

SELECT * FROM enriched
