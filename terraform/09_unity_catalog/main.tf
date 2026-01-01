terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.58"
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

provider "databricks" {
  alias      = "account"
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.databricks_account_id
  auth_type  = "azure-cli"
}

data "terraform_remote_state" "databricks" {
  backend = "local"
  config = {
    path = "../04_databricks_workspace/terraform.tfstate"
  }
}

data "terraform_remote_state" "storage" {
  backend = "local"
  config = {
    path = "../07_storage/terraform.tfstate"
  }
}

data "terraform_remote_state" "access_connector" {
  backend = "local"
  config = {
    path = "../08_access_connector/terraform.tfstate"
  }
}

data "azurerm_databricks_workspace" "main" {
  name                = data.terraform_remote_state.databricks.outputs.databricks_workspace_name
  resource_group_name = var.resource_group_name
}

provider "databricks" {
  alias                       = "workspace"
  host                        = data.azurerm_databricks_workspace.main.workspace_url
  azure_workspace_resource_id = data.azurerm_databricks_workspace.main.id
  auth_type                   = "azure-cli"
}

resource "random_pet" "metastore" {
  length    = 2
  separator = "-"
}

locals {
  metastore_name   = var.metastore_name != null ? var.metastore_name : "${var.metastore_name_prefix}-${random_pet.metastore.id}"
  storage_account  = data.terraform_remote_state.storage.outputs.storage_account_name
  container_name   = data.terraform_remote_state.storage.outputs.storage_container_name
  storage_root     = var.metastore_storage_root != null ? var.metastore_storage_root : "abfss://${local.container_name}@${local.storage_account}.dfs.core.windows.net/uc"
  metastore_region = var.metastore_region != null ? var.metastore_region : data.azurerm_databricks_workspace.main.location
  external_url     = var.external_location_url != null ? var.external_location_url : "abfss://${local.container_name}@${local.storage_account}.dfs.core.windows.net/"
  metastore_id     = var.existing_metastore_id != null ? var.existing_metastore_id : try(databricks_metastore.main[0].id, null)
}

resource "databricks_metastore" "main" {
  count        = var.existing_metastore_id == null ? 1 : 0
  provider     = databricks.account
  name         = local.metastore_name
  region       = local.metastore_region
  storage_root = local.storage_root
}

resource "databricks_metastore_data_access" "main" {
  provider     = databricks.account
  metastore_id = local.metastore_id
  name         = var.metastore_data_access_name

  azure_managed_identity {
    access_connector_id = data.terraform_remote_state.access_connector.outputs.access_connector_id
  }
}

resource "databricks_metastore_assignment" "main" {
  provider             = databricks.account
  metastore_id         = local.metastore_id
  workspace_id         = var.workspace_id
  default_catalog_name = var.default_catalog_name
}

resource "databricks_storage_credential" "main" {
  provider = databricks.workspace
  name     = var.storage_credential_name

  azure_managed_identity {
    access_connector_id = data.terraform_remote_state.access_connector.outputs.access_connector_id
  }
}

resource "databricks_external_location" "main" {
  provider        = databricks.workspace
  name            = var.external_location_name
  url             = local.external_url
  credential_name = databricks_storage_credential.main.name
}
