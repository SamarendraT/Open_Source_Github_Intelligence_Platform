# ── OPTIONAL service principal ─────────────────────────────────────────────────
# All guarded by var.create_service_principal. Leave it false if your subscription
# is in a university-managed tenant that disables app registration (the azuread
# provider would fail with 403 Authorization_RequestDenied). The pipeline does not
# need this SP — Unity Catalog reaches ADLS via the access connector's managed
# identity. Enable only to demo the classic "SP creds in Key Vault secret scope" flow.

data "azuread_client_config" "current" {}

resource "azuread_application" "etl" {
  count        = var.create_service_principal ? 1 : 0
  display_name = "sp-${var.prefix}-etl"
  owners       = [data.azuread_client_config.current.object_id]
}

resource "azuread_service_principal" "etl" {
  count     = var.create_service_principal ? 1 : 0
  client_id = azuread_application.etl[0].client_id
  owners    = [data.azuread_client_config.current.object_id]
}

resource "azuread_application_password" "etl" {
  count          = var.create_service_principal ? 1 : 0
  application_id = azuread_application.etl[0].id
  display_name   = "etl-secret"
}

resource "azurerm_role_assignment" "sp_storage" {
  count                = var.create_service_principal ? 1 : 0
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.etl[0].object_id
}
