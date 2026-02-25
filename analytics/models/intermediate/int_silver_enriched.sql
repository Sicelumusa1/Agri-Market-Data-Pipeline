-- joins staging tables to create the enriched silver layer.


{{ config(
    materialized='table',
    partition_by={
        'field': 'scrape_date',
        'data_type': 'date'
    },
    cluster_by=['market', 'commodity']
) }}

WITH summary AS (
    SELECT * FROM {{ ref('stg_market_summary') }}
),

container AS (
    SELECT * FROM {{ ref('stg_market_container') }}
),

variety AS (
    SELECT * FROM {{ ref('stg_market_variety') }}
),

-- Add date dimensions using a macro
date_dimensions AS (
    SELECT 
        *,
        {{ date_dimensions('scrape_date') | indent(8) }}
    FROM variety
),

-- Join variety with container to get container-level metrics
variety_with_container AS (
    SELECT 
        v.*,
        container.average_price_per_kg AS container_avg_price_per_kg,
        container.kg_sold AS container_kg_sold,
        container.value_sold AS container_value_sold
    FROM date_dimensions v
    LEFT JOIN container 
        ON v.scrape_date = container.scrape_date
        AND v.market = container.market
        AND v.commodity = container.commodity
        AND v.container_name = container.container_name
),

-- summary-level context
enriched AS (
    SELECT 
        v.*,
        s.kg_sold AS total_market_kg,
        s.value_sold AS total_market_value,
        
        -- Calculate percentages
        CASE 
            WHEN s.kg_sold > 0 AND v.kg_sold >= 0 
            THEN LEAST(ROUND(SAFE_DIVIDE(v.kg_sold, s.kg_sold) * 100, 2), 100)
            WHEN s.kg_sold > 0 AND v.kg_sold < 0 
            THEN GREATEST(ROUND(SAFE_DIVIDE(v.kg_sold, s.kg_sold) * 100, 2), 0)
            ELSE NULL
        END AS market_share_percent_by_kg,
        
        -- Price comparisons
        ROUND(v.average_price_per_kg - v.container_avg_price_per_kg, 2) 
            AS price_vs_container_avg,
            
        ROUND(v.average_price_per_kg - (s.value_sold / NULLIF(s.kg_sold, 0)), 2) 
            AS price_vs_market_avg
        
    FROM variety_with_container v
    LEFT JOIN summary s 
        ON v.scrape_date = s.scrape_date
        AND v.market = s.market
        AND v.commodity = s.commodity
)

SELECT * FROM enriched