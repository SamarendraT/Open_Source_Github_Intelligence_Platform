resource "azurerm_resource_group" "this" {
  name     = "rg-${var.prefix}"
  location = var.location
  tags     = var.tags
}

# Who am I, per Azure — supplies tenant_id and my object_id for Key Vault access grants.
data "azurerm_client_config" "current" {}
