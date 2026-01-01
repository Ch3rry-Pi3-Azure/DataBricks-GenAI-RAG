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

data "azurerm_databricks_workspace" "main" {
  name                = data.terraform_remote_state.databricks.outputs.databricks_workspace_name
  resource_group_name = var.resource_group_name
}

provider "databricks" {
  host                        = data.azurerm_databricks_workspace.main.workspace_url
  azure_workspace_resource_id = data.azurerm_databricks_workspace.main.id
  auth_type                   = "azure-cli"
}

locals {
  resolved_display_name = var.display_name != null ? var.display_name : "dbx-sp"
}

resource "databricks_service_principal" "main" {
  application_id = var.application_id
  display_name   = local.resolved_display_name
}

resource "databricks_service_principal" "account" {
  provider       = databricks.account
  application_id = var.application_id
  display_name   = local.resolved_display_name
}

resource "databricks_entitlements" "main" {
  service_principal_id   = databricks_service_principal.main.id
  workspace_access       = var.workspace_access
  allow_cluster_create   = var.allow_cluster_create
  allow_instance_pool_create = var.allow_instance_pool_create
  databricks_sql_access  = var.databricks_sql_access
}
