# Gold Layer Documentation

## What is Gold?
The gold layer represents **decision-ready intelligence** optimized for specific farmer questions. Each gold table is designed to answer one clear question family with minimal query complexity.

## Key Characteristics
| **Attribute** | **Description** |
|--------------|-----------------|
| **Grain** | Aggregated (varies by table) |
| **Source** | dbt transformations from silver |
| **Destination** | BigQuery dataset: `gold` |
| **Update** | Daily (scheduled) + On-demand |
| **Access** | Looker Studio, analysts, farmers |

## Design Philosophy

### 1. Question-Driven Design
Each gold table answers exactly one question family:

| **Table** | **Core Question** | **Farmer Decision** |
|----------|-------------------|---------------------|
| `daily_market_snapshot` | "What should I sell today?" | Today's harvest |
| `time_pattern_analysis` | "When should I sell?" | Harvest schedule |
| `product_optimization` | "What configuration should I pack?" | Packaging choice |
| `market_trends_analysis` | "Where is the market heading?" | Farm strategy |

### 2. Denormalized Star Schema
We embed dimensions directly in fact tables because:
-  **Faster queries**: No joins = instant dashboard loads
-  **Simpler for farmers**: One table per dashboard page
-  **Cheaper**: Less data scanned per query
-  **Easier to understand**: "This table tells me what to sell today"

### 3. Pre-Aggregation Strategy

| **Aggregation Level** | **Why** |
|----------------------|---------|
| Daily by variety | Most common farmer query |
| Weekly patterns | Identify trends without recalc |
| Monthly trends | Strategic planning |
| Product combinations | Compare options instantly |

### 4. Update Frequencies

Daily at 4 PM:
  - Refresh daily_market_snapshot (today's data)
  - Update time_pattern_analysis (7-day rolling)
  - Recalculate product_optimization scores
  - Append to market_trends_analysis

Monthly on 1st:
  - Full refresh of time_pattern_analysis
  - Recalculate confidence scores
  - Update seasonal patterns

### 5. Table Types

|Table  |	Type    |	Partitioning    |	Why |
|-----------------------|-------------|----------|--------------------------------|
|daily_market_snapshot  |	Time-series |	By date |	Farmers always filter by date   |
|time_pattern_analysis  |	Reference   |	None    |	Small table, always scanned fully   |
|product_optimization   |	Reference   |	None    |	Product master data |
|market_trends_analysis |	Time-series |	By date |	Historical trend analysis   |

### How Farmers Consume Gold

Farmer opens Looker Studio → 
  Dashboard queries ONE gold table → 
    Results in < 2 seconds →
      Makes decision (sell today, pack this container)

### Quality Gates

Each gold table must have:

- Clear question it answers

- Documented grain (what's one row?)

- Partitioning/clustering strategy

- Update frequency defined

- Sample queries documented

- Known limitations listed

### Key Principle

***"Gold is decision-ready, not data-ready."***
Every column should help a farmer decide something.