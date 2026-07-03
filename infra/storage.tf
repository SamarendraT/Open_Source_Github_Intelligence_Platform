resource "azurerm_storage_account" "adls" {
  name                     = "st${var.prefix}${var.unique_suffix}" # 3-24 chars, lowercase alphanumeric only
  resource_group_name      = azurerm_resource_group.this.name
  location                 = azurerm_resource_group.this.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # locally-redundant is fine for dev; GRS would double storage cost for nothing here
  account_kind             = "StorageV2"
  is_hns_enabled           = true # hierarchical namespace — THIS flag is what makes it ADLS Gen2, not plain Blob

  # This lake is Entra ID-only: no anonymous blobs, no account-key/SAS bypass of RBAC.
  # Every access path (access connector MI, optional SP, az CLI --auth-mode login) is identity-based.
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  default_to_oauth_authentication = true

  tags = var.tags
}

# One block, four medallion containers. DRY applies to infrastructure too.
resource "azurerm_storage_container" "layers" {
  for_each              = toset(["raw", "bronze", "silver", "gold", "catalog"])
  name                  = each.key
  storage_account_id    = azurerm_storage_account.adls.id
  container_access_type = "private"
}
