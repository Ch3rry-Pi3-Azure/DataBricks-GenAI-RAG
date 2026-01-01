variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "endpoint_name" {
  type        = string
  description = "Vector Search endpoint name"
  default     = "vector_search_endpoint"
}

variable "permission_level" {
  type        = string
  description = "Permission level to grant on the endpoint"
  default     = "CAN_MANAGE"
}

variable "service_principal_application_id" {
  type        = string
  description = "Optional override for the service principal application ID"
  default     = null
}

variable "skip_if_missing" {
  type        = bool
  description = "Skip if the endpoint is not found"
  default     = false
}
