resource "azurerm_databricks_workspace" "this" {
  name                        = "dbw-${var.prefix}"
  resource_group_name         = azurerm_resource_group.this.name
  location                    = azurerm_resource_group.this.location
  sku                         = "premium" # Standard tier is retired; Premium also unlocks Unity Catalog + secret ACLs
  managed_resource_group_name = "rg-${var.prefix}-managed"
  tags                        = var.tags
}

# Managed identity Unity Catalog uses to reach ADLS — the modern replacement for
# mounting storage with service-principal secrets in Spark configs. Creating this
# needs only Owner/Contributor on the RG (an ARM op), NOT Entra directory rights —
# so it works even if your tenant blocks app registration.
resource "azurerm_databricks_access_connector" "uc" {
  name                = "dbac-${var.prefix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = var.tags

  identity {
    type = "SystemAssigned"
  }
}

# Let the access connector's managed identity read/write the lake.
resource "azurerm_role_assignment" "uc_storage" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.uc.identity[0].principal_id
}

resource "azurerm_role_assignment" "uc_storage_file_events" {
  for_each = toset([
    "Storage Queue Data Contributor",
    "Storage Account Contributor",
    "EventGrid EventSubscription Contributor",
  ])
  scope                = azurerm_storage_account.adls.id
  role_definition_name = each.key
  principal_id         = azurerm_databricks_access_connector.uc.identity[0].principal_id
}


# Owner grants control-plane only; browsing data in the portal / az CLI
# needs an explicit data-plane role for the human operator too.
resource "azurerm_role_assignment" "me_storage" {
  scope                = azurerm_storage_account.adls.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}