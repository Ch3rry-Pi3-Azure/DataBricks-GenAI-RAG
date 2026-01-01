variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "endpoint_name" {
  type        = string
  description = "Databricks serving endpoint name"
  default     = "basic-chatbot-endpoint"
}

variable "served_model_name" {
  type        = string
  description = "Name for the served model inside the endpoint"
  default     = "basic-chatbot"
}

variable "model_name" {
  type        = string
  description = "Registered MLflow model name (e.g. catalog.schema.model or model_name)"
  default     = "basic-chatbot"
}

variable "model_version" {
  type        = string
  description = "Model version to serve"
  default     = "1"
}

variable "secret_scope_name" {
  type        = string
  description = "Databricks secret scope name for serving environment variables"
  default     = "aoai-scope"
}

variable "databricks_sp_secret_scope_name" {
  type        = string
  description = "Databricks secret scope name for service principal credentials"
  default     = "dbx-sp-scope"
}

variable "databricks_client_id_secret_name" {
  type        = string
  description = "Secret name for Databricks service principal client ID"
  default     = "dbx-client-id"
}

variable "databricks_client_secret_name" {
  type        = string
  description = "Secret name for Databricks service principal client secret"
  default     = "dbx-client-secret"
}

variable "databricks_tenant_id_secret_name" {
  type        = string
  description = "Secret name for Azure tenant ID"
  default     = "dbx-tenant-id"
}

variable "workload_size" {
  type        = string
  description = "Serving workload size (Small, Medium, Large)"
  default     = "Small"
}

variable "scale_to_zero_enabled" {
  type        = bool
  description = "Enable scale-to-zero for the serving endpoint"
  default     = true
}

variable "traffic_percentage" {
  type        = number
  description = "Traffic percentage for the served model"
  default     = 100
}
