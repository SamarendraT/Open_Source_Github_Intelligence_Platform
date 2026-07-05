# Build Progress

Phase-by-phase log. Full plan: `DE_Project_Plan_GitHub_Ecosystem_Intelligence.md` (kept outside this repo).

## Phase 0 — Foundation & Guardrails
- [x] Problem statement + business questions in README
- [x] Repo skeleton (`infra/ bundle/ src/ notebooks/ tests/ docs/ .github/workflows/`)
- [x] `.gitignore` + secrets policy decided (Key Vault + secret scopes; `.env` local only, never committed)
- [x] `git init` + first commit
- [x] GitHub repo created + pushed
- [x] Databricks Free Edition account created  ← **primary build/demo env** (see ADR-001)
- [x] Azure Cost Management budget = **$50** (annual) with alerts at 50/75/90% (alert-only; credit is the real hard stop)

> **Student-account constraints verified 2026-07-03 — see `docs/DECISIONS.md` ADR-001 & ADR-002.**
> Region-lock policy, 4–6 vCPU cap, no Spot, optional SP. **Build-once portfolio artifact,
> ≤ $50.** Strategy: hybrid — Free Edition for heavy build/backfill, Azure Databricks for
> cloud-proof evidence. Orchestration is built & proven once, then the schedule is paused.

## Phase 1 — Provision Infrastructure (Terraform)
- [x] Terraform written (RG, ADLS Gen2 raw/bronze/silver/gold, Databricks workspace Premium, access connector, Key Vault, optional SP) — `infra/`
- [x] **Install Terraform + Azure CLI** (`winget install Hashicorp.Terraform Microsoft.AzureCLI`)
- [x] **Pre-flight** (`infra/README.md`) — results 2026-07-03: allowed regions = `centralindia, koreacentral, malaysiawest, austriaeast, eastasia` → **centralindia** chosen; SP creation **allowed** (personal tenant) → `create_service_principal = true`; `terraform.tfvars` filled
- [x] vCPU quota check — all 5 allowed regions identical: Total Regional 6, DSv2/DSv3/FSv2/DASv4 = 4 each → `Standard_DS3_v2` single-node fits in centralindia
- [x] `terraform init` / `validate` / `plan` / `apply` — **Apply complete 2026-07-03: 19 added, 0 errors.** Workspace `https://adb-7405610850603620.0.azuredatabricks.net`, storage `stghintelts02`, KV `kv-ghintel-ts02`, connector `dbac-ghintel`
- [ ] (optional, anytime before Phase 8) `terraform destroy` → re-`apply` to prove reproducibility
- [x] Key Vault–backed secret scope `gh-intel` (verified: `dbutils.secrets.list` → 3 secrets)
- [x] Single-node, auto-terminating (10 min) cluster — node type **`Standard_E4as_v4`** (32 GB), NOT DS3_v2: hidden student-sub SKU restrictions block D4ds_v4/D4s_v3 (`NotAvailableForSubscription`) and centralindia doesn't offer DS3_v2/F4s_v2 at all; E4as_v4 + D4as_v4 were the only startable 4-core options (D4as_v4 absent from Databricks dropdown)
- [x] Unity Catalog: storage credential `cred-ghintel` (access connector MI) → 5 external locations (raw/bronze/silver/gold/catalog, all tested) → catalog `ghintel` + `bronze/silver/gold` schemas pinned to their containers
- [x] File-events roles added for Auto Loader notifications (queue/EventGrid/account contributor on the connector MI) + `Microsoft.EventGrid` provider registered
- [x] **End-to-end smoke test passed 2026-07-03**: secret scope + `CREATE/SELECT/DROP ghintel.bronze._smoke` through the full chain
- [x] Operator data-plane access (`me_storage` role) for portal browsing — Owner alone has no data rights (by design)

## Phase 2 — Ingestion → Bronze

> **Constraint found 2026-07-03:** Free Edition serverless blocks DNS for non-allowlisted
> hosts (`data.gharchive.org` → gaierror -3; pypi resolves fine) and the egress policy is
> not user-configurable. Adaptation: downloader is developed/tested **locally** (stdlib-only,
> `dest_dir` param makes it env-agnostic) and runs for real on the **Azure** cluster (full
> egress); FE Auto Loader dev uses a few hourly files **uploaded manually** into
> `workspace.bronze.landing` via the Catalog UI.

- [x] GH Archive downloader (parameterized date range, re-runnable, skips landed files) — dev locally, prod on Azure
- [x] Sample hours uploaded to FE landing volume (manual, one-time)
- [x] Auto Loader raw → bronze (schema evolution, `payload` forced STRING via schema hints, checkpointing, ingest metadata, partitioned)
- [x] Idempotency verified (re-run = zero new rows)

## Phase 3 — Bronze → Silver ✔ (completed 2026-07-03)
- [x] JSON flattening — schema-aware `_nested` handles struct OR json-string bronze (`src/transforms/silver.py`)
- [x] Dedup via insert-only Delta MERGE on event_id (batch-internal row_number dedup first)
- [x] Type casting + derived event_date/event_hour; is_bot = `[bot]` OR `-bot` heuristic
- [x] DQ tagging + quarantine table — **618,600 valid + 4 quarantined (null_repo_id) = 618,604 distinct bronze ids**; bad-data drill verified (`null_event_id`, `bad_timestamp` caught end-to-end)
- [x] Pure functions in /src (`tag_quality` returns ONE df — see ADR-004: serverless foreachBatch is one-shot; writer materializes to `silver._batch_staging` then fans out to MERGE + quarantine)
- Note for Phase 4: 2026 events carry no `payload.size` → `push_size` is NULL for current data; the daily mart counts *pushes*, not commits.

## Phase 4 — Silver → Gold
- [ ] dim_repo (SCD Type 2), dim_actor, dim_date, dim_event_type
- [ ] fact_events, fact_repo_daily_metrics, fact_language_trends
- [ ] Business-question SQL (window functions, CTEs)
- [ ] OPTIMIZE + Z-ORDER + benchmark (before/after numbers)

## Phase 5 — Orchestration
- [ ] Databricks Workflow: ingest → bronze → silver → gold on Jobs Compute
- [ ] Retries, failure alerts, daily schedule, date parameterization

## Phase 6 — Testing & CI/CD
- [ ] pytest + chispa unit tests on /src functions
- [ ] GitHub Actions: lint (ruff) → test → deploy via Asset Bundles
- [ ] databricks.yml Asset Bundle definition

## Phase 7 — Serving & Visualization
- [ ] Dashboard (Databricks SQL or Power BI) — 4–6 visuals + "so what" insights

## Phase 8 — Documentation & Presentation
- [ ] Architecture diagram, data dictionary, runbook
- [ ] "What I'd do differently at scale" writeup
- [ ] Cost report (actual spend vs $80)

---

## Environment Notes

- **Local machine:** Python 3.14 + Java 26 — local Spark 3.5 will NOT start (needs Python ≤3.12 and Java 17). Options for Phase 6: install Java 17 + a Python 3.12 venv for local pytest, or run Spark tests only in GitHub Actions CI. Decide in Phase 6.
- **CLIs to install** (needed from Phase 1): Terraform, Azure CLI, Databricks CLI. `gh` optional.
- **Dev split:** ~90% of build/backfill on Databricks Free Edition ($0); Azure runs bounded slices only, for integration proof.
