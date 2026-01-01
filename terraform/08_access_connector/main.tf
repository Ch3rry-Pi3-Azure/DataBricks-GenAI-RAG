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

data "terraform_remote_state" "storage" {
  backend = "local"
  config = {
    path = "../07_storage/terraform.tfstate"
  }
}

data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

resource "random_pet" "connector" {
  length    = 2
  separator = "-"
}

locals {
  connector_name = var.access_connector_name != null ? var.access_connector_name : "${var.access_connector_name_prefix}-${random_pet.connector.id}"
}

resource "azurerm_databricks_access_connector" "main" {
  name                = local.connector_name
  location            = coalesce(var.location, data.azurerm_resource_group.main.location)
  resource_group_name = data.azurerm_resource_group.main.name

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_role_assignment" "storage_blob_contributor" {
  scope                = data.terraform_remote_state.storage.outputs.storage_account_id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_databricks_access_connector.main.identity[0].principal_id
}
