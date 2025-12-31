variable "resource_group_name" {
  type        = string
  description = "Name of the existing resource group"
}

variable "location" {
  type        = string
  description = "Azure region for the storage account (defaults to RG location if null)"
  default     = null
}

variable "storage_account_name" {
  type        = string
  description = "Name of the storage account (lowercase only). If null, uses storage_account_name_prefix + random suffix."
  default     = null
}

variable "storage_account_name_prefix" {
  type        = string
  description = "Prefix used to build the storage account name when storage_account_name is null"
  default     = "stgdbgenai"
}

variable "account_tier" {
  type        = string
  description = "Storage account tier"
  default     = "Standard"
}

variable "account_replication_type" {
  type        = string
  description = "Storage account replication type"
  default     = "LRS"
}

variable "is_hns_enabled" {
  type        = bool
  description = "Enable hierarchical namespace (ADLS Gen2)"
  default     = true
}

variable "container_name" {
  type        = string
  description = "Name of the storage container"
  default     = "rag-data"
}

variable "grant_current_principal_access" {
  type        = bool
  description = "Grant Storage Blob Data Contributor to the current Terraform principal (for seed uploads)"
  default     = true
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the storage account"
  default     = {}
}
