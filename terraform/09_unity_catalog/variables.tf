variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "databricks_account_id" {
  type        = string
  description = "Databricks account ID (from the Databricks account console)"
}

variable "workspace_id" {
  type        = number
  description = "Databricks workspace ID from the account console API"
}

variable "metastore_name" {
  type        = string
  description = "Unity Catalog metastore name (if null, uses metastore_name_prefix + random suffix)"
  default     = null
}

variable "existing_metastore_id" {
  type        = string
  description = "Use an existing metastore ID instead of creating a new one"
  default     = null
}

variable "metastore_name_prefix" {
  type        = string
  description = "Prefix used to build the metastore name when metastore_name is null"
  default     = "uc-metastore"
}

variable "metastore_region" {
  type        = string
  description = "Region for the metastore (defaults to workspace location if null)"
  default     = null
}

variable "metastore_storage_root" {
  type        = string
  description = "Storage root for the metastore (defaults to abfss://<container>@<account>.dfs.core.windows.net/uc)"
  default     = null
}

variable "default_catalog_name" {
  type        = string
  description = "Default catalog name for the metastore assignment"
  default     = "main"
}

variable "metastore_data_access_name" {
  type        = string
  description = "Name for the metastore data access configuration"
  default     = "metastore-access"
}

variable "storage_credential_name" {
  type        = string
  description = "Name of the Unity Catalog storage credential"
  default     = "uc-storage-credential"
}

variable "external_location_name" {
  type        = string
  description = "Name of the Unity Catalog external location"
  default     = "uc-external-location"
}

variable "external_location_url" {
  type        = string
  description = "External location URL (defaults to abfss://<container>@<account>.dfs.core.windows.net/)"
  default     = null
}
