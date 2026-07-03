terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.9" # 4.9.0+ required: storage_account_id on azurerm_storage_container
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id     = var.subscription_id # required in azurerm v4 — no implicit subscription
  storage_use_azuread = true                # data-plane calls use Entra ID, consistent with shared keys being disabled
}

provider "azuread" {}
