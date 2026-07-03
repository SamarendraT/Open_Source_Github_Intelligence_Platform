resource "azurerm_key_vault" "this" {
  name                       = "kv-${var.prefix}-${var.unique_suffix}" # globally unique, 3-24 chars
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true # RBAC roles, not legacy access policies
  soft_delete_retention_days = 7
  tags                       = var.tags
}

# I need to WRITE secrets (RBAC data-plane role, distinct from control-plane Contributor).
resource "azurerm_role_assignment" "kv_me" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# The AzureDatabricks first-party service needs to READ secrets — this is what makes
# a Key Vault-backed secret scope work. If this errors with "service principal not
# found", the first-party app isn't provisioned in your tenant yet; run once:
#   az ad sp create --id 2ff814a6-3304-4ab8-85cb-cd0e6f879c1d
# then re-apply.
data "azuread_service_principal" "azure_databricks" {
  client_id = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d" # well-known global AzureDatabricks app ID
}

resource "azurerm_role_assignment" "kv_databricks" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = data.azuread_service_principal.azure_databricks.object_id
}

# A non-sensitive secret so the Key Vault-backed secret scope has something to read
# even when the service principal is disabled. depends_on because the RBAC grant
# above must propagate before the data-plane write succeeds (retry apply on 403).
resource "azurerm_key_vault_secret" "tenant_id" {
  name         = "sp-tenant-id"
  value        = data.azurerm_client_config.current.tenant_id
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_me]
}

# ── SP credentials in Key Vault (only when the SP exists) ──────────────────────
resource "azurerm_key_vault_secret" "sp_client_id" {
  count        = var.create_service_principal ? 1 : 0
  name         = "sp-client-id"
  value        = azuread_application.etl[0].client_id
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_me]
}

resource "azurerm_key_vault_secret" "sp_client_secret" {
  count        = var.create_service_principal ? 1 : 0
  name         = "sp-client-secret"
  value        = azuread_application_password.etl[0].value
  key_vault_id = azurerm_key_vault.this.id
  depends_on   = [azurerm_role_assignment.kv_me]
}
