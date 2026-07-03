output "workspace_url" {
  description = "Open this to reach your Databricks workspace."
  value       = "https://${azurerm_databricks_workspace.this.workspace_url}"
}

output "storage_account_name" {
  value = azurerm_storage_account.adls.name
}

output "key_vault_uri" {
  description = "DNS name — used when creating the Databricks secret scope."
  value       = azurerm_key_vault.this.vault_uri
}

output "key_vault_id" {
  description = "Resource ID — also used for the secret scope."
  value       = azurerm_key_vault.this.id
}

output "access_connector_id" {
  description = "Feed this into the Unity Catalog storage credential."
  value       = azurerm_databricks_access_connector.uc.id
}
