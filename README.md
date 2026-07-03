# GitHub Ecosystem Intelligence

> An end-to-end lakehouse on **Azure + Databricks** built on the public GitHub event firehose ([GH Archive](https://www.gharchive.org/)) — ingesting millions of events per day into a Bronze → Silver → Gold Delta Lake architecture that answers real business questions about the open-source ecosystem. Developed for **~$0** on Databricks Free Edition and demonstrated on Azure for **under $50**.

---

## The Problem

A developer-tools company (a database vendor, a CI/CD startup, or a VC's technical due-diligence team) needs to spot emerging open-source projects and technology shifts *before* they become obvious, and to understand how contributor communities form and retain. No off-the-shelf product gives a clean, queryable, historical view of the entire public GitHub activity stream sliced by the metrics they care about.

This platform ingests the raw public GitHub event stream, cleans and models it into an analytics-ready warehouse, and answers:

1. **Momentum** — which repositories are gaining stars/forks fastest this week vs last?
2. **Technology trends** — how is activity shifting across programming languages and topics over time?
3. **Community health** — new vs. returning contributors per repo; contributor retention; bus-factor signals.
4. **Activity patterns** — event-type mix (pushes, PRs, issues, releases) and how it changes by time-of-day and day-of-week.
5. **Rising stars** — repositories with the steepest growth in the most recent period.

## The Dataset

[GH Archive](https://www.gharchive.org/) publishes the public GitHub event stream as gzipped hourly JSON files (`https://data.gharchive.org/YYYY-MM-DD-H.json.gz`):

- **Genuinely big** — millions of events/day; a few months is billions of rows. Spark is justified for real, not as a toy.
- **Semi-structured & nested** — deeply nested JSON with arrays: real schema handling, flattening, and exploding.
- **Naturally incremental** — a new file every hour: the perfect shape for incremental ingestion and idempotent loads.
- **Free, reliable, no API keys, no rate limits.**

## Architecture

**Pattern: Medallion (Bronze → Silver → Gold) lakehouse on Delta Lake.**

```
GH Archive (hourly .json.gz)
        │  ingestion (download → land)
        ▼
┌──────────────────────────────────────────────────────────────┐
│ ADLS Gen2  (raw landing zone)                                │
└──────────────────────────────────────────────────────────────┘
        │  Auto Loader (cloudFiles): incremental, schema evolution, checkpointed
        ▼
   BRONZE  ── append-only raw events + ingest metadata (Delta)
        │  parse/flatten JSON · dedup by event_id (MERGE) · type cast · DQ checks
        ▼
   SILVER  ── cleansed, conformed, deduplicated events (Delta)  ──▶ quarantine table
        │  dimensional modeling · aggregation · SCD Type 2
        ▼
   GOLD    ── dim_repo · dim_actor · dim_date · dim_event_type
              fact_events · fact_repo_daily_metrics · fact_language_trends (Delta)
        │  OPTIMIZE + Z-ORDER + partitioning
        ▼
   SERVING ── Databricks SQL dashboard  /  Power BI
```

- **Orchestration:** Databricks Workflows (task dependencies, retries, daily schedule, failure alerts) on Jobs Compute.
- **Governance:** Unity Catalog (schemas per layer, lineage, access control).
- **Deployment:** Databricks Asset Bundles (Databricks objects) + Terraform (Azure infrastructure) via GitHub Actions CI/CD.
- **Secrets:** Azure Key Vault–backed secret scopes. Nothing sensitive is ever committed.

## Tech Stack

| Layer | Technology |
|---|---|
| Ingestion | Python + Databricks Auto Loader (`cloudFiles`) |
| Storage | ADLS Gen2 + Delta Lake |
| Processing | PySpark on Azure Databricks |
| Modeling | Star schema, SCD Type 2, medallion layers |
| Orchestration | Databricks Workflows (Jobs Compute) |
| Governance | Unity Catalog |
| IaC | Terraform (Azure) + Databricks Asset Bundles |
| CI/CD | GitHub Actions (lint → test → deploy) |
| Testing | pytest + chispa |
| Serving | Databricks SQL dashboard / Power BI |

## Repository Structure

```
/infra              ← Terraform (Azure resources)
/bundle             ← Databricks Asset Bundle (jobs, pipelines)
/src                ← PySpark transformation modules (pure functions)
/notebooks          ← thin orchestration notebooks that call /src
/tests              ← pytest + chispa unit tests
/docs               ← architecture diagram, data dictionary, runbook, progress
/.github/workflows  ← CI/CD
```

## Cost Story

Built for **~$0** (developed on Databricks Free Edition) and demonstrated on Azure for **under $50**: heavy build and historical backfill on free serverless, Azure limited to a few bounded runs on a single-node cluster, 10-minute auto-terminate, resource tagging, and an Azure Cost Management budget with alerts at 50/75/90%. A build-once portfolio artifact — the scheduled pipeline is built and proven, then paused. Full cost report and the student-account constraints I engineered around are in [docs/DECISIONS.md](docs/DECISIONS.md).

## Status

🚧 **In progress** — see [docs/PROGRESS.md](docs/PROGRESS.md) for the phase-by-phase build log.
