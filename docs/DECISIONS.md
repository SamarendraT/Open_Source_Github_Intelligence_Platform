# Design Decisions & Constraints

A running log of *why* the project is built the way it is. These double as interview
talking points — "I hit a real constraint and engineered around it" beats "I followed a tutorial."

## ADR-001: Azure for Students changes the execution strategy (not the architecture)

**Date:** 2026-07-03
**Context:** Deploying to an Azure for Students subscription ($100 / 12 months, no card).
Verified against Microsoft Learn + Databricks docs + first-hand reports (2024–2026).

**Constraints discovered:**

1. **Region lock (since ~Aug 2025).** An "Allowed resource deployment regions" Deny
   policy restricts *all* resources to ~5 regions that vary per account and can't be
   changed. → `location` is a required Terraform variable set only after a pre-flight
   policy check; nothing is hardcoded.
2. **Compute cap: 4–6 total regional vCPUs, non-increasable.** Only a single-node,
   4-core cluster (`Standard_DS3_v2`) can start; multi-node is impossible; some accounts
   show quota 0 for all Databricks-compatible families.
3. **No Spot VMs on student subscriptions.** Moot here — a single-node cluster is
   driver-only and the Databricks driver is always on-demand regardless.
4. **Cost Management is best-effort.** Azure for Students is an unsupported Cost
   Management offer: data lags up to 72h and may be incomplete. Authoritative credit
   balance is the Sponsorships portal (microsoftazuresponsorships.com/balance). The
   credit itself is the hard stop — at $100 the subscription auto-disables (this is the
   real safety net; there is no surprise-bill risk).
5. **Service principal may be blocked.** University-managed tenants often disable app
   registration (Terraform `azuread` 403s). → SP is optional (`create_service_principal`,
   default false); Unity Catalog reaches ADLS via the access connector's managed identity,
   which needs no directory permission.

**Decision:**
- **Primary build + demo environment = Databricks Free Edition** (serverless, Unity
  Catalog included, $0, none of the above limits). ~90% of the pipeline is built and
  the historical backfill runs here.
- **Azure = bounded "cloud proof"**: Terraform stands up the real infra (demonstrates
  IaC — this works fine), then *one* single-node run for screenshots/lineage/metrics.
- **Fallback ladder if the classic cluster won't start:** serverless jobs on the same
  workspace → Databricks Free Edition (Microsoft's sanctioned student path) → upgrade to
  pay-as-you-go.

**Consequences for the skills story:** every skill in the plan's matrix stays
demonstrable. Two talking points get *stronger*:
- Auth: "managed identity via access connector, no secrets to rotate" (current best
  practice) instead of "SP creds in Key Vault."
- FinOps: "single-node driver-only is on-demand by design; I bounded Azure data volume
  and did the heavy backfill on free serverless" instead of the (inapplicable) spot story.

**Revisit if:** the account is upgraded to pay-as-you-go, or moved to a personal-MSA
tenant (both remove the region lock, quota cap, and SP block).

---

## ADR-002: This is a build-once portfolio artifact, budget ceiling $50

**Date:** 2026-07-03
**Context:** The goal is a profile/portfolio centerpiece, not an operating pipeline.
It gets built once, produces evidence (screenshots, lineage, metrics, dashboard, cost
report), and is then left dormant. Target Azure spend: **≤ $50** of the $100 credit.

**Decisions:**
- **Hybrid, deliberately:** Databricks Free Edition for heavy/iterative build + the
  historical backfill ($0); Azure Databricks for the real-cloud evidence (both are used,
  per the explicit ask). Same code runs in both — only the target storage/catalog differ.
- **Orchestration (Phase 5) is built and *proven*, not left running.** Create the
  scheduled Workflow, trigger it 1–2 times to capture successful runs + retry behaviour +
  DAG screenshots, then **pause/disable the schedule**. A dormant, screenshot-documented
  pipeline is the portfolio artifact; a daily job silently draining credit is a liability.
- **Azure compute is a few bounded runs, then stop.** Ingest only a few days of GH Archive
  on Azure (the big backfill is on Free Edition). Realistic Azure spend is single-digit
  dollars; $50 is a comfortable ceiling with a wide margin.
- **Budget = $50** in Cost Management with 50/75/90% alerts (alert-only; the credit
  auto-disable at $100 is the true hard stop). Verify real balance at the Sponsorships
  portal, since Cost Management is best-effort on this offer (ADR-001 #4).

**Consequence:** every phase deliverable is still produced. "Built once, documented,
cost-controlled" is exactly the FinOps maturity the plan wants to signal.
