-- Select only needed columns
-- Rename columns to consistent naming
-- Do minimal type casting


WITH source AS (
    SELECT * FROM {{ source('market_data', 'market_container') }}
),

renamed AS (
    SELECT
        -- Primary keys and identifiers
        {{ dbt_utils.generate_surrogate_key(['scrape_date', 'market', 'commodity', 'container_name']) }} 
            AS container_id,
        scrape_date,
        market,
        commodity,
        container_name,
        
        -- Metrics
        value_sold,
        value_sold_mtd,
        qty_sold,
        qty_sold_mtd,
        kg_sold,
        kg_sold_mtd,
        qty_available,
        average_price_per_kg,
        
        -- Metadata
        file_date,
        _dlt_load_id,
        _dlt_id,
        
        -- Audit
        CURRENT_TIMESTAMP() AS dbt_loaded_at
        
    FROM source
)

SELECT * FROM renamed