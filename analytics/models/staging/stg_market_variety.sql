-- Select only needed columns
-- Rename columns to consistent naming
-- Do minimal type casting


WITH source AS (
    SELECT * FROM {{ source('market_data', 'market_variety') }}
),

renamed AS (
    SELECT
        -- Primary keys and identifiers
        {{ dbt_utils.generate_surrogate_key([
            'scrape_date', 
            'market', 
            'commodity', 
            'container_name', 
            'variety',
            'product_class'
        ]) }} AS variety_id,
        
        scrape_date,
        market,
        commodity,
        container_name,
        variety,
        
        -- Parsed product attributes (from dlt)
        product_class AS grade,
        product_size AS size_value,
        product_count AS count_per_container,
        product_color AS color,
        original_product_string,
        
        -- Container info
        unit_mass,
        
        -- Metrics
        value_sold,
        qty_sold,
        kg_sold,
        average_price,
        highest_price,
        average_price_per_kg,
        highest_price_per_kg,
        
        -- Derived (calculated for consistency)
        ROUND(SAFE_DIVIDE(value_sold, NULLIF(qty_sold, 0)), 2) AS calculated_avg_price_per_unit,
        
        -- Metadata
        file_date,
        _dlt_load_id,
        _dlt_id,
        
        -- Audit
        CURRENT_TIMESTAMP() AS dbt_loaded_at
        
    FROM source
)

SELECT * FROM renamed