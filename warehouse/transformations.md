# Transformations: dlt vs dbt Responsibilities

## Overview
This document defines where transformation logic lives in our pipeline, ensuring clear boundaries between ingestion (dlt) and business logic (dbt).

## Transformation Boundaries

Raw CSV → [dlt] → Silver → [dbt] → Gold → [Looker]

## What dlt Handles (Ingestion Layer)

### dlt Responsibilities
| **Task** | **Why in dlt** |
|---------|---------------|
| CSV parsing | File format concerns |
| Date standardization | Data type conversion |
| Currency cleaning | Remove 'R', commas, negatives |
| Combined field splitting | "MTD:" values → daily + mtd |
| Product combination parsing | "AFRI BLUSH,CL 1,150,8,RED" → components |
| Schema evolution handling | New columns don't break pipeline |
| Null handling | Replace empty strings with NULL |

### dlt Code Example
```python
@dlt.resource
def clean_currency(value):
    # Handles: "R3,311,589.00" → 3311589.00
    # Also: "R-8,320.00" → -8320.00
    return float(str(value).replace('R', '').replace(',', ''))
```

## What dbt Handles (Transformation Layer)

### dbt Responsibilities
| ***Task***  |	***Why in dbt*** |
|---------|---------------|
| Joins |	Combine silver tables |
| Aggregations |	Daily totals, averages |
| Rankings  |	Price ranks, top performers |
| Business logic    |	Container recommendations |
| Derived metrics   |	Optimization scores |
| Data quality tests    |	schema.yml validation |
| Documentation	    | Model descriptions |

### dbt Code Example
```sql
-- Business logic lives here, not in dlt
price_rank_within_commodity = ROW_NUMBER() OVER (
    PARTITION BY market_date, commodity 
    ORDER BY avg_price_per_kg DESC
)
```

## What dbt Must NEVER Do

### dbt Prohibited Tasks
|   ***Task***  |	***Why Not***   |	***Where It Belongs***  |
|---------|---------------|--------------------|
String parsing  |	Should be done at ingestion |	dlt |
Currency cleaning   |	Data type conversion    |	dlt |
Handling missing columns    |	Schema evolution    |	dlt |
File format handling    |	Source-specific |	dlt |

### Why This Separation?

***Benefits***

1. Clear ownership: No debate about where logic lives

2. Performance: Heavy parsing once (dlt), analytics many times (dbt)

3. Maintainability: Change business rules without reprocessing raw data

4. Testing: Unit tests for parsing (dlt) separate from logic tests (dbt)

5. Reproducibility: Silver is stable, gold can be rebuilt



### Data Lineage Example
```yaml
Raw CSV: "R3,311,589.00MTD: R29,361,407.00"

dlt:
  ↓ total_value_sold_daily = 3311589.00
  ↓ total_value_sold_mtd = 29361407.00

Silver:
  ↓ stored as FLOAT64 in silver_enriched_data

dbt:
  ↓ daily_market_snapshot.avg_price_per_kg
  ↓ daily_market_snapshot.price_rank_within_commodity
```

## Testing Strategy

### dlt Tests

- Can parse all expected CSV formats

- Handles schema changes gracefully

- Correct type conversion

### dbt Tests

- Referential integrity

- Accepted value ranges

- Unique keys

- Business logic correctness

### Key Principle

- `"Parse in dlt, decide in dbt."`
- Let dlt handle the messy reality of files; let dbt handle the clean world of analytics.