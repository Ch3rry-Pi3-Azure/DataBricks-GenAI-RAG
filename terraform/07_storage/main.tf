terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

resource "random_pet" "storage" {
  length    = 2
  separator = ""
}

locals {
  account_name = var.storage_account_name != null ? lower(var.storage_account_name) : lower(substr("${var.storage_account_name_prefix}${random_pet.storage.id}", 0, 24))
}

resource "azurerm_storage_account" "main" {
  name                     = local.account_name
  location                 = coalesce(var.location, data.azurerm_resource_group.main.location)
  resource_group_name      = data.azurerm_resource_group.main.name
  account_tier             = var.account_tier
  account_replication_type = var.account_replication_type
  is_hns_enabled           = var.is_hns_enabled
  min_tls_version          = "TLS1_2"
  tags                     = var.tags
}

resource "azurerm_storage_container" "data" {
  name                  = var.container_name
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_role_assignment" "current_principal_blob_contributor" {
  count                = var.grant_current_principal_access ? 1 : 0
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.current.object_id
}
