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

data "terraform_remote_state" "databricks" {
  backend = "local"
  config = {
    path = "../04_databricks_workspace/terraform.tfstate"
  }
}

data "terraform_remote_state" "service_principal" {
  backend = "local"
  config = {
    path = "../06_databricks_service_principal/terraform.tfstate"
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
  sp_app_id      = var.service_principal_application_id != null ? var.service_principal_application_id : data.terraform_remote_state.service_principal.outputs.service_principal_application_id
  sp_display_name = data.terraform_remote_state.service_principal.outputs.service_principal_display_name
  principal_name  = var.principal_name != null ? var.principal_name : local.sp_app_id
}

resource "databricks_grants" "catalog" {
  catalog = var.catalog_name

  grant {
    principal  = local.principal_name
    privileges = ["USE_CATALOG"]
  }
}

resource "databricks_grants" "schema" {
  schema = var.schema_name

  grant {
    principal  = local.principal_name
    privileges = ["USE_SCHEMA", "CREATE_TABLE"]
  }
}

resource "databricks_grants" "table" {
  table = var.table_name

  grant {
    principal  = local.principal_name
    privileges = ["SELECT"]
  }
}

resource "databricks_grants" "index_table" {
  count = var.index_table_name != null && var.index_table_name != "" ? 1 : 0
  table = var.index_table_name

  grant {
    principal  = local.principal_name
    privileges = ["SELECT"]
  }
}
