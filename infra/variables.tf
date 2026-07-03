variable "subscription_id" {
  type        = string
  description = "Azure subscription GUID (from: az account show --query id -o tsv)."
}

variable "location" {
  type        = string
  description = <<-DESC
    Azure region for ALL resources. On Azure for Students this is NOT free choice:
    a subscription-level "Allowed resource deployment regions" Deny policy limits you
    to ~5 regions that vary per account. Run the pre-flight in infra/README.md and set
    this to a region that is (a) policy-allowed, (b) Databricks-supported, and
    (c) has >=4 vCPU quota in a Databricks-compatible VM family (DSv2/Dsv3/Fsv2).
  DESC
  # No default on purpose — you must consciously set a region your policy allows.
}

variable "prefix" {
  type        = string
  default     = "ghintel"
  description = "Short name stem for resources."
}

variable "unique_suffix" {
  type        = string
  description = "3-6 lowercase alphanumerics. Storage & Key Vault names are GLOBALLY unique across all of Azure."
}

variable "create_service_principal" {
  type        = bool
  default     = false
  description = <<-DESC
    Create an Entra app registration + service principal for non-interactive auth.
    Leave FALSE if your subscription lives in a university-managed tenant that
    disables app registration (Terraform would 403). Default auth path is:
    interactive `az login` (you as Owner) + the Databricks access connector
    (managed identity) for Unity Catalog -> ADLS. Set TRUE only if your pre-flight
    `az ad app create` test succeeds and you want the Key Vault secret-scope demo.
  DESC
}

variable "tags" {
  type = map(string)
  default = {
    project = "gh-intel"
    env     = "dev"
  }
  description = "Applied to every resource so cost shows up per-project in Cost Management."
}
