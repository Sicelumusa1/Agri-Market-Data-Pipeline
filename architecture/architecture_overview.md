# Market Data Platform – Architecture Overview

## Executive Summary

The Market Data Platform is a cloud-native analytical data platform designed to ingest, process, and analyze fresh produce market data from multiple markets across South Africa.

The platform implements a **modern medallion architecture (Bronze → Silver → Gold)**, combining the durability and flexibility of a data lake with the analytical performance of a cloud data warehouse. The system is event-driven, cost-efficient, and built to scale as additional markets and analytical use cases are introduced.

The architecture prioritizes:
- Preservation of raw historical data
- Strong separation of concerns across pipeline stages
- Cost-aware, serverless execution
- Analytics-engineering best practices

---

## High-Level Architecture

![Data Flow Diagram](data_flow_diagram.png)

---

## Core Design Principles

1. **Scalability**  
   - Horizontal scaling across markets (Joburg, Pretoria, future markets)
   - Parallel processing of independent data files

2. **Cost Optimization**  
   - Serverless compute (Cloud Run)
   - Event-driven execution (EventArc)
   - Separation of cold (GCS) and hot (BigQuery) data

3. **Maintainability**  
   - Clear ownership per layer (ingestion, cleansing, analytics)
   - Tool specialization (dlt ≠ dbt)
   - Version-controlled infrastructure and pipelines

4. **Reliability**  
   - Explicit completion signals (`UPLOAD_DONE`)
   - Idempotent pipelines
   - Retry and failure handling via orchestration

5. **Extensibility**  
   - Easy onboarding of new markets
   - Schema evolution handled gracefully
   - Gold layer designed to evolve iteratively

---

## Technology Stack

| Layer | Technology | Justification |
|-----|-----------|--------------|
| Data Lake | Google Cloud Storage | Cheap, durable, scalable object storage |
| Event Routing | EventArc | Native GCS event handling |
| Serverless Compute | Cloud Run | Auto-scale to zero, container-based |
| Orchestration | Kestra | Declarative DAGs, strong observability |
| Cleansing | dlt | Schema evolution, parquet staging, Python flexibility |
| Warehouse | BigQuery | Serverless analytics, partitioning & clustering |
| Analytics | dbt | SQL-only business logic, testing, documentation |
| Visualization | Looker Studio | Native BigQuery integration |
| Ingestion Trigger | GitHub Actions | Cost-effective, secure, scheduled execution |

---

## Architecture Layers Overview

### Ingestion Layer
- Web scraper extracts fresh produce market data
- GitHub Actions checks source freshness before execution
- Data uploaded to GCS using Workload Identity Federation

### Processing Layer
- EventArc detects upload completion
- Cloud Run validates trigger condition
- Kestra orchestrates dlt-based cleaning pipeline

### Analytics & Consumption Layer
- Cleaned data stored in BigQuery (Silver)
- dbt applies business logic (Gold)
- Looker Studio consumes materialized views only

---

## Key Workflows Summary

### Ingestion Workflow
1. Scheduled GitHub Actions job runs
2. Source site checked for updates
3. Scraper runs only if new data exists
4. Files uploaded to GCS by market and type
5. `UPLOAD_DONE` marker file uploaded

### Processing Workflow
1. EventArc detects new GCS object
2. Cloud Run checks for completion marker
3. Kestra DAG executes dlt pipeline
4. Data cleaned, standardized, and loaded to BigQuery
5. dbt models update Gold layer and views
6. Looker Studio dashboards refresh

---

## Future Considerations

- Additional market onboarding
- Incremental processing strategies
- Advanced data quality SLAs
- Machine learning feature layers
- External data APIs
