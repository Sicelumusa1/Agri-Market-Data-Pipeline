# Design Decisions & Rationale

## Medallion Architecture

**Decision:** Use Bronze–Silver–Gold layering.

**Why:**
- Preserves raw data
- Separates cleansing from analytics
- Enables scalable analytics engineering
- Aligns with industry best practices

---

## dlt for Silver Layer

**Decision:** Perform heavy transformations in dlt.

**Why:**
- Complex parsing is cleaner in Python
- Built-in schema evolution
- Parquet staging optimizes BigQuery ingestion
- dbt remains SQL-only and business-focused

**Trade-offs:**
- Additional pipeline complexity
- Python environment management

---

## Event-Driven Processing

**Decision:** EventArc + Cloud Run trigger.

**Why:**
- No polling
- No idle compute costs
- Naturally fits irregular data arrival patterns
- Reliable and observable

---

## Kestra for Orchestration

**Decision:** Use Kestra for DAG execution.

**Why:**
- Declarative workflows
- Strong retry and error handling
- Excellent visibility
- Easy future extensibility

---

## ELT over ETL

**Decision:** Transform inside BigQuery.

**Why:**
- BigQuery compute is cheap and scalable
- Enables reprocessing without re-ingestion
- Encourages analytical flexibility

---

## Security via Materialized Views

**Decision:** BI tools access views only.

**Why:**
- Strong access control
- Query cost predictability
- Clean business-facing schema

---

## File Completion Marker

**Decision:** Use `UPLOAD_DONE` file.

**Why:**
- Guarantees full dataset availability
- Simplifies orchestration logic
- Prevents partial processing

---

## Open Design Decisions

- Gold layer aggregation depth
- Incremental vs full refresh strategy
- Long-term raw data retention
- Data quality SLAs
- Alerting thresholds
