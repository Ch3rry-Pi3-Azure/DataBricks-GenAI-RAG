variable "resource_group_name" {
  type        = string
  description = "Name of the existing resource group"
}

variable "location" {
  type        = string
  description = "Azure region for the access connector (defaults to RG location if null)"
  default     = null
}

variable "access_connector_name" {
  type        = string
  description = "Name of the Databricks access connector (if null, uses access_connector_name_prefix + random suffix)"
  default     = null
}

variable "access_connector_name_prefix" {
  type        = string
  description = "Prefix used to build the access connector name when access_connector_name is null"
  default     = "dbac-genai"
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the access connector"
  default     = {}
}
