variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "secret_scope_name" {
  type        = string
  description = "Name of the Databricks secret scope backed by Key Vault"
  default     = "aoai-scope"
}

variable "databricks_sp_secret_scope_name" {
  type        = string
  description = "Name of the Databricks secret scope for service principal credentials"
  default     = "dbx-sp-scope"
}

variable "cluster_name" {
  type        = string
  description = "Name of the Databricks cluster"
  default     = "GenAI Cluster"
}

variable "data_security_mode" {
  type        = string
  description = "Data security mode for the cluster"
  default     = "DATA_SECURITY_MODE_AUTO"
}

variable "single_user_name" {
  type        = string
  description = "User name for SINGLE_USER clusters (usually your Databricks login email)"
  default     = null
}

variable "runtime_engine" {
  type        = string
  description = "Runtime engine (e.g., PHOTON)"
  default     = "PHOTON"
}

variable "kind" {
  type        = string
  description = "Cluster kind"
  default     = "CLASSIC_PREVIEW"
}

variable "spark_version" {
  type        = string
  description = "Databricks runtime version"
  default     = null
}

variable "node_type_id" {
  type        = string
  description = "Worker node type ID"
  default     = null
}

variable "autotermination_minutes" {
  type        = number
  description = "Minutes of inactivity before auto-termination"
  default     = 120
}

variable "is_single_node" {
  type        = bool
  description = "Whether to create a single-node cluster"
  default     = true
}

variable "use_ml_runtime" {
  type        = bool
  description = "Use Databricks ML runtime image"
  default     = true
}

variable "mlflow_enable_db_sdk" {
  type        = string
  description = "Enable MLflow DB SDK auth (set as cluster env var)"
  default     = "true"
}

variable "databricks_pat_secret_name" {
  type        = string
  description = "Secret name for Databricks PAT in the secret scope"
  default     = "databricks-pat"
}

variable "openai_pypi_package" {
  type        = string
  description = "PyPI package spec for the OpenAI SDK"
  default     = "openai==1.56.0"
}

variable "vectorsearch_pypi_package" {
  type        = string
  description = "PyPI package spec for Databricks Vector Search"
  default     = "databricks-vectorsearch"
}

variable "azure_identity_pypi_package" {
  type        = string
  description = "PyPI package spec for Azure Identity"
  default     = "azure-identity"
}

variable "databricks_sdk_pypi_package" {
  type        = string
  description = "PyPI package spec for Databricks SDK"
  default     = "databricks-sdk"
}
