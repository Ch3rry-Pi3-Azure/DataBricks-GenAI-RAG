terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.2"
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

locals {
  service_principal_app_id = var.service_principal_application_id != null ? var.service_principal_application_id : data.terraform_remote_state.service_principal.outputs.service_principal_application_id
  script_path              = replace(abspath("${path.root}/../../scripts/vector_search_permissions.py"), "'", "''")
}

resource "null_resource" "vector_search_permissions" {
  triggers = {
    endpoint_name      = var.endpoint_name
    permission_level   = var.permission_level
    service_principal  = local.service_principal_app_id
    workspace_resource = data.azurerm_databricks_workspace.main.id
  }

  provisioner "local-exec" {
    interpreter = ["PowerShell", "-NoProfile", "-Command"]
    command     = "& python '${local.script_path}' --host '${data.azurerm_databricks_workspace.main.workspace_url}' --workspace-resource-id '${data.azurerm_databricks_workspace.main.id}' --endpoint-name '${var.endpoint_name}' --service-principal-app-id '${local.service_principal_app_id}' --permission-level '${var.permission_level}'${var.skip_if_missing ? " --skip-if-missing" : ""}"
  }
}
