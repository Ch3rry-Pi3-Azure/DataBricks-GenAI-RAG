variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "catalog_name" {
  type        = string
  description = "Unity Catalog catalog name"
  default     = "adb_genai_super_locust"
}

variable "schema_name" {
  type        = string
  description = "Unity Catalog schema name (catalog.schema)"
  default     = "adb_genai_super_locust.rag"
}

variable "table_name" {
  type        = string
  description = "Unity Catalog table name (catalog.schema.table)"
  default     = "adb_genai_super_locust.rag.diabetes_faq_table"
}

variable "index_table_name" {
  type        = string
  description = "Optional Unity Catalog index table name (catalog.schema.table)"
  default     = null
}

variable "service_principal_application_id" {
  type        = string
  description = "Optional override for the service principal application ID"
  default     = null
}

variable "principal_name" {
  type        = string
  description = "Optional override for the principal name to grant (e.g. <appId>, dbx-sp, or servicePrincipal:<appId>)"
  default     = null
}
