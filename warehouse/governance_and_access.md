# Governance & Access Control

## Overview
This document defines who can access what data and how we protect both data quality and cost through governance policies.

## Access Hierarchy
                                                    ┌─────────────────┐
                                                    │   BigQuery      │
                                                    └────────┬────────┘
                                                             │
                                                   ┌────────────────────┐
                                                   │                    │
                                                   ▼                    ▼
                            ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
                            │ Bronze        │ │ Silver        │ │ Gold          │
                            │ (GCS)         │ │ (BigQuery)    │ │ (BigQuery)    │
                            │ • Raw CSVs    │ │ • Cleaned     │ │ • Aggregated  │
                            │ • No access   │ │ • Internal    │ │ • Dashboard   │
                            └───────────────┘ └───────────────┘ └───────────────┘
                                                                        │
                                                                        ▼
                                                                    ┌───────────────┐
                                                                    │ Looker        │
                                                                    │ Studio        │
                                                                    │ • Farmers     │
                                                                    │ • Public      │
                                                                    └───────────────┘


## Access by Layer

### Bronze Layer (GCS)
| **Role** | **Access** | **Why** |
|---------|-----------|---------|
| Data Engineers | Write | Upload scraped CSVs |
| dlt service account | Read | Ingestion pipeline |
| Everyone else |  No access | Raw data, no business value |

### Silver Layer (BigQuery)
| **Role** | **Access** | **Why** |
|---------|-----------|---------|
| dbt service account | Read/Write | Transformations |
| Data Engineers | Read | Debugging |
| Data Analysts | Read (with approval) | Ad-hoc analysis |
| Looker Studio |  No direct access | Too granular, would be slow/costly |
| Farmers |  No access | Not decision-ready |

### Gold Layer (BigQuery)
| **Role** | **Access** | **Why** |
|---------|-----------|---------|
| Looker Studio | Read | Dashboard source |
| Data Analysts | Read | Advanced analysis |
| Data Engineers | Read | Monitoring |
| dbt service account | Write | Refresh models |
| Farmers |  No direct access | Use Looker instead |

### Looker Studio (Dashboard)
| **Role** | **Access** | **Why** |
|---------|-----------|---------|
| Farmers | View only | Make decisions |
| Market managers | View + Filter | Market oversight |
| Public |  No access | Internal tool |

## Why This Separation?

### Protect Data Quality
- Raw data never exposed (prevents misinterpretation)
- Silver schema controlled (no accidental changes)
- Gold tables curated (only validated metrics)

### Protect Costs
| **Layer** | **Query Cost** | **Protection** |
|----------|---------------|---------------|
| Silver | High (full scans) | Only internal use |
| Gold | Low (aggregated) | Dashboard-friendly |
| Looker | Cached | Repeated views free |

### Protect Privacy
- No farmer-specific data (aggregated only)
- No individual transaction data
- Market-level insights only

## Implementation

### BigQuery IAM Roles
```yaml
# Service Accounts
dlt-sa@project.iam.gserviceaccount.com:
  roles:
    - roles/bigquery.dataEditor (silver dataset)
    - roles/bigquery.jobUser

dbt-sa@project.iam.gserviceaccount.com:
  roles:
    - roles/bigquery.dataEditor (gold dataset)
    - roles/bigquery.dataViewer (silver dataset)
    - roles/bigquery.jobUser

looker-sa@project.iam.gserviceaccount.com:
  roles:
    - roles/bigquery.dataViewer (gold dataset)
    - roles/bigquery.jobUser
```

### Row-Level Security
```sql
-- Example: Future multi-farmer support
CREATE ROW ACCESS POLICY farmer_filter
ON gold.daily_market_snapshot
GRANT TO ('user:farmer@example.com')
FILTER USING (commodity = 'apples' AND region = 'Western Cape')
```

## Data Quality Gates

### Silver to Gold Promotion

Each gold model must pass:
- Not null tests on key columns

- Accepted value ranges (price > 0)

- Unique keys (no duplicates)

- Referential integrity

### Dashboard Access

Looker Studio only sees:

- Materialized gold tables

- Cached results (4-hour TTL)

- Pre-aggregated data (no raw)

### Audit & Monitoring
Query Audit
```sql
-- Track who's querying what
SELECT 
  user_email,
  query,
  total_bytes_processed,
  creation_time
FROM `region-us`.INFORMATION_SCHEMA.JOBS_BY_USER
WHERE creation_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
ORDER BY creation_time DESC
```

### Cost Alerts
```yaml

# Budget alerts at:
- $100/month: Warning
- $300/month: Review access
- $500/month: Emergency review
```

## Incident Response

### If Someone Queries Silver Accidentally

1. Identify user from audit logs

2. Revoke temporary access

3. Educate on proper gold layer usage

4. Add additional guardrails if needed

### If Costs Spike

1. Check for full table scans
2. Verify partitioning is working

3. Review Looker caching settings

4. Check for new user access

### Key Principle

- `"Default deny, explicit allow."`
- No one gets access by default. Every access is justified and documented.