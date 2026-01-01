variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "databricks_account_id" {
  type        = string
  description = "Databricks account ID for account-level SCIM objects"
}

variable "application_id" {
  type        = string
  description = "Azure AD application (client) ID for the service principal"
}

variable "display_name" {
  type        = string
  description = "Display name for the Databricks service principal"
  default     = null
}

variable "workspace_access" {
  type        = bool
  description = "Grant workspace access entitlement"
  default     = true
}

variable "allow_cluster_create" {
  type        = bool
  description = "Allow the service principal to create clusters"
  default     = false
}

variable "allow_instance_pool_create" {
  type        = bool
  description = "Allow the service principal to create instance pools"
  default     = false
}

variable "databricks_sql_access" {
  type        = bool
  description = "Grant Databricks SQL access entitlement"
  default     = false
}
