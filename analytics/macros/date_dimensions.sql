
{% macro date_dimensions(date_column) %}
    -- This macro extracts various date components for time-based analysis
    
    EXTRACT(YEAR FROM {{ date_column }}) AS year,
    EXTRACT(MONTH FROM {{ date_column }}) AS month,
    EXTRACT(DAY FROM {{ date_column }}) AS day_of_month,
    EXTRACT(DAYOFWEEK FROM {{ date_column }}) AS day_of_week_num,
    FORMAT_DATE('%A', {{ date_column }}) AS day_name,
    EXTRACT(WEEK FROM {{ date_column }}) AS week_of_year,
    
    -- Week in month (1-4)
    CASE 
        WHEN EXTRACT(DAY FROM {{ date_column }}) BETWEEN 1 AND 7 THEN 1
        WHEN EXTRACT(DAY FROM {{ date_column }}) BETWEEN 8 AND 14 THEN 2
        WHEN EXTRACT(DAY FROM {{ date_column }}) BETWEEN 15 AND 21 THEN 3
        ELSE 4
    END AS week_in_month,
    
    -- Season (Southern Hemisphere)
    CASE 
        WHEN EXTRACT(MONTH FROM {{ date_column }}) IN (12, 1, 2) THEN 'Summer'
        WHEN EXTRACT(MONTH FROM {{ date_column }}) IN (3, 4, 5) THEN 'Autumn'
        WHEN EXTRACT(MONTH FROM {{ date_column }}) IN (6, 7, 8) THEN 'Winter'
        ELSE 'Spring'
    END AS season,
    
    -- Weekend flag
    CASE 
        WHEN EXTRACT(DAYOFWEEK FROM {{ date_column }}) IN (1, 7) THEN 1
        ELSE 0
    END AS is_weekend,
    
    -- Month start/end for cash flow analysis
    EXTRACT(DAY FROM {{ date_column }}) <= 5 AS is_month_start,
    EXTRACT(DAY FROM {{ date_column }}) >= 25 AS is_month_end

{% endmacro %}