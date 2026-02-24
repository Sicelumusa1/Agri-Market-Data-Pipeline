# AgriMarket Analytics - Data Warehouse Documentation

## Overview
This folder documents the analytical data warehouse powering the AgriMarket Insights platform. Built on Google BigQuery, this warehouse transforms daily agricultural market CSV files into decision-ready intelligence for farmers and market stakeholders.

## Technology Stack
| **Component** | **Technology** | **Purpose** |
|--------------|----------------|-------------|
| Ingestion | dlt | CSV parsing, schema evolution, bronze → silver |
| Transformations | dbt | Business logic, aggregations, gold layer |
| Storage & Compute | BigQuery | Serverless warehouse, partitioning, clustering |
| Visualization | Looker Studio | Farmer-facing dashboards |

## Layer Architecture
Bronze (GCS) → dlt → Silver (BigQuery) → dbt → Gold (BigQuery) → Looker
Raw CSV Clean Analytics-Ready Decision Dashboard
Data Clean Data Models


## Quick Start
1. **Start with**: `warehouse_overview.md` for the mental model
2. **Understand layers**: `layers/silver_layer.md` and `layers/gold_layer.md`
3. **Explore models**: `models/` directory for each gold table
4. **Performance**: `partitioning_and_clustering.md` for cost optimization
5. **Security**: `governance_and_access.md` for data protection

## Key Principles
- **ELT over ETL**: BigQuery does the heavy lifting
- **Decision-driven design**: Each gold table answers one farmer question
- **Denormalized for speed**: Joins = friction, farmers won't wait
- **Honest about uncertainty**: Confidence bands, data quality indicators
