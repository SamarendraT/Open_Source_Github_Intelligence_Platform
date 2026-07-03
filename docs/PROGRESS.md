# Build Progress

Phase-by-phase log. Full plan: `DE_Project_Plan_GitHub_Ecosystem_Intelligence.md` (kept outside this repo).

## Phase 0 — Foundation & Guardrails
- [x] Problem statement + business questions in README
- [x] Repo skeleton (`infra/ bundle/ src/ notebooks/ tests/ docs/ .github/workflows/`)
- [x] `.gitignore` + secrets policy decided (Key Vault + secret scopes; `.env` local only, never committed)
- [ ] `git init` + first commit
- [ ] GitHub repo created + pushed
- [ ] Databricks Free Edition account created
- [ ] Azure resource group created
- [ ] Azure Cost Management budget = $80 with alerts at 50/75/90%

## Phase 1 — Provision Infrastructure (Terraform)
- [ ] Terraform: RG, ADLS Gen2 (containers: raw/bronze/silver/gold), Databricks workspace (Premium), Key Vault, service principal + role assignment
- [ ] `terraform apply` → `destroy` → re-`apply` (prove reproducibility)
- [ ] Key Vault–backed secret scope in Databricks
- [ ] Single-node, auto-terminating, spot cluster config
- [ ] Unity Catalog: catalog + bronze/silver/gold schemas

## Phase 2 — Ingestion → Bronze
- [ ] GH Archive downloader (parameterized date range, re-runnable, skips landed files)
- [ ] Auto Loader raw → bronze (schema evolution, checkpointing, ingest metadata, partitioned)
- [ ] Idempotency verified (re-run = zero new rows)

## Phase 3 — Bronze → Silver
- [ ] JSON flattening (event_id, type, actor, repo, org, created_at; explode payloads)
- [ ] Dedup via Delta MERGE on event_id
- [ ] Type casting + derived event_date/event_hour
- [ ] DQ expectations + quarantine table
- [ ] Transformations as pure functions in /src

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
