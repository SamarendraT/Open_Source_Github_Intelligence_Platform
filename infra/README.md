# Infrastructure (Terraform)

Provisions the Azure footprint: resource group, ADLS Gen2 (raw/bronze/silver/gold),
Databricks workspace (Premium), Unity Catalog access connector, Key Vault, and
(optionally) a service principal.

> **Azure for Students note.** This subscription has hard, non-negotiable limits that
> older tutorials predate. Do the **pre-flight** below *before* `terraform apply` — it
> discovers the two things Terraform can't guess: which regions you're allowed to
> deploy in, and whether you can create a service principal. Skipping it means
> `apply` fails halfway with a policy or quota error.

---

## Pre-flight (run once, ~5 minutes)

```bash
az login
az account show --query id -o tsv          # copy this GUID -> subscription_id in terraform.tfvars
```

### 1. Which regions am I allowed to deploy in?

Azure for Students enforces an "Allowed resource deployment regions" **Deny** policy.
The allowed set varies per account and cannot be changed.

```bash
az policy assignment list --query "[?contains(displayName,'region') || contains(displayName,'location')].{name:displayName, params:parameters}" -o json
```

If that's empty, read the effective allowed locations from the policy directly:

```bash
az policy assignment list -o json > assignments.json   # then open it and find the
                                                        # "Allowed locations" / allowedLocations parameter
```

Pick one region from that list for `location`. It must ALSO be a Databricks-supported
region. Note the exact region name (e.g. `centralindia`, `swedencentral`, `eastus2`).

### 2. Do I have vCPU quota for a Databricks node there?

Replace `<region>` with your chosen region:

```bash
az vm list-usage --location <region> -o table | grep -Ei "Total Regional|DSv2|Dsv3|Fsv2|Dav4|Dasv4"
```

You need **>= 4** on **Total Regional vCPUs** AND on at least one Databricks-compatible
family (`Standard DSv2 Family`, `Standard Dsv3 Family`, or `Standard FSv2 Family`).
`Standard_DS3_v2` (4 vCPU, DSv2 family) is the target node type. If every relevant
family shows **0**, classic clusters won't start here — you'll use serverless / Free
Edition instead (see repo README cost strategy). Confirm the size actually exists in
the region:

```bash
az vm list-skus --location <region> --size Standard_DS3 --output table
```

### 3. Can I create a service principal? (decides `create_service_principal`)

```bash
az ad app create --display-name permcheck-delete-me
```

- **Succeeds** → you may set `create_service_principal = true`. Clean up:
  `az ad app delete --id <appId from the output>`
- **"Insufficient privileges to complete the operation"** → keep it `false`. Your
  tenant blocks app registration; the managed-identity path handles everything.

---

## Deploy

```bash
cp terraform.tfvars.example terraform.tfvars   # then edit with your real values
terraform init                                 # downloads providers + writes .terraform.lock.hcl (commit the lock)
terraform fmt
terraform validate
terraform plan                                 # READ every line: ~N to add, 0 to destroy
terraform apply                                # type 'yes' when the plan looks right
```

### Known first-run hiccups (all normal)

| Symptom | Cause | Fix |
|---|---|---|
| `403` writing a Key Vault secret | RBAC role assignment still propagating | Re-run `terraform apply` (it's incremental) |
| `service principal was not found` (kv_databricks) | AzureDatabricks first-party app not yet in tenant | `az ad sp create --id 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d`, re-apply |
| `RequestDisallowedByPolicy` / `Allowed resource deployment regions` | `location` isn't on your allowed list | Change `location` to an allowed region (step 1) |
| storage/Key Vault "name already taken" | someone globally has your suffix | Change `unique_suffix`, re-apply |

## Prove reproducibility (interview line: "my whole footprint is one command")

```bash
terraform destroy
terraform apply
```

## Commit / never-commit

- **Commit:** all `*.tf`, `.terraform.lock.hcl`, `terraform.tfvars.example`
- **Never commit:** `terraform.tfvars`, `*.tfstate*`, `.terraform/` (already in `.gitignore`)
