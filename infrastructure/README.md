# Agri‑Market‑Data‑Pipeline – Infrastructure Guide

This document explains **how infrastructure is structured, deployed, and managed** for this repository.

It is written for **future‑me** on a tired day. Clarity > cleverness.

---

## High‑level goals

* Use **Infrastructure as Code (Terraform)** to manage all GCP resources
* Support **two environments**: `dev` and `prod`
* Use **one GitHub repo**, **one codebase**
* Keep **mental overhead low** and **debugging predictable**

---

## Environments

We run **two completely separate GCP projects**:
e.g

| Environment | GCP Project                 |
| ----------- | --------------------------- |
| Dev         | `farm-market-insights-dev`  |
| Prod        | `farm-market-insights-prod` |

Why separate projects?

* Strong isolation (no accidental prod damage)
* Simple IAM reasoning
* Easy destroy / recreate in dev

---

## Repository structure (important)

Only the **infrastructure directory** is environment‑aware.

All other directories (`ingestion`, `analytics`, `orchestration`, etc.) are **environment‑agnostic** and use configuration at runtime.

```
├── infrastructure
│   ├── bootstrap
│   │   ├── dev
│   │   │   ├── iam.tf
│   │   │   ├── main.tf
│   │   │   ├── outputs.tf
│   │   │   ├── providers.tf
│   │   │   ├── terraform.tfstate
│   │   │   ├── terraform.tfstate.backup
│   │   │   ├── terraform.tfvars
│   │   │   └── variables.tf
│   │   └── prod
│   │       ├── iam.tf
│   │       ├── main.tf
│   │       ├── outputs.tf
│   │       ├── providers.tf
│   │       ├── terraform.tfstate
│   │       ├── terraform.tfstate.backup
│   │       ├── terraform.tfvars
│   │       └── variables.tf
│   ├── env
│   │   ├── dev
│   │   │   ├── backend.tf
│   │   │   ├── gcs.tf
│   │   │   ├── iam.tf
│   │   │   ├── main.tf
│   │   │   ├── outputs.tf
│   │   │   ├── providers.tf
│   │   │   ├── terraform.tfvars
│   │   │   └── variables.tf
│   │   └── prod
│   │       ├── backend.tf
│   │       ├── gcs.tf
│   │       ├── iam.tf
│   │       ├── main.tf
│   │       ├── outputs.tf
│   │       ├── providers.tf
│   │       ├── terraform.tfvars
│   │       └── variables.tf
│   └── README.md

```

There is **intentional duplication** between `dev` and `prod`.

This is a feature, not a bug.

---

## Bootstrap layer (read this carefully)

`bootstrap/` is **not normal infrastructure**.

It exists only to create **identity and trust**, nothing else.

### What bootstrap does

* Creates Terraform service accounts
* Creates GitHub **Workload Identity Pool**
* Binds GitHub repos to service accounts

### What bootstrap does NOT do

* Create buckets
* Create datasets
* Create pipelines
* Run automatically

### How often bootstrap runs

* **Once per GCP project**
* Manually
* Slowly

If bootstrap is wrong, **everything else will fail**.

---

## GitHub repositories & permissions

We use **two different GitHub repos with different permissions**.

| Repo                            | Purpose               | Permissions                      |
| ------------------------------- | --------------------- | -------------------------------- |
| `Agri-Market-Data-Pipeline`     | Infra + orchestration | Can create/update GCP resources  |
| `market-data-ingestion-scraper` | Data ingestion only   | Can write objects to GCS buckets |

This prevents ingestion code from accidentally creating or modifying infrastructure.

---

## Infrastructure environments

Each environment directory is **fully self‑contained**.

### Example: dev

```
cd infrastructure/env/dev
terraform init
terraform plan
terraform apply
```

The same applies to prod.

There is **no shared state** between environments.

---

## Terraform state

Each environment:

* Uses its own Terraform state
* Targets a single GCP project

State is **never shared** between dev and prod.

---

## Branching strategy

e.g

| Git branch | Environment                 |
| ---------- | --------------------------- |
| `dev`      | `farm-market-insights-dev`  |
| `main`     | `farm-market-insights-prod` |

Rules:

* All changes start in `dev`
* Dev is applied and validated first
* Only then is a PR merged into `main`

No direct changes to prod.

---

## CI/CD philosophy

* Dev can be broken
* Prod must be boring

Automation increases **only when understanding increases**.

Manual steps are acceptable if they reduce risk.

---

## Common mistakes (learned the hard way)

* Mixing IAM for multiple repos in one binding
* Reusing service accounts across environments
* Trying to be "too DRY" too early
* Debugging IAM without writing conditions down

If something feels confusing: **stop and simplify**.

---

## Rebuild policy

Because this is IaC:

* Dev can be destroyed and recreated at any time
* No manual changes should exist in the console
* If state and reality drift → rebuild

Reproducibility is the goal.

---

## Final rule (non‑negotiable)

> If future‑me is confused, past‑me failed.

Always optimize for **clarity over cleverness**.
