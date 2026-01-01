output "metastore_id" {
  value = local.metastore_id
}

output "metastore_name" {
  value = try(databricks_metastore.main[0].name, null)
}

output "metastore_data_access_name" {
  value = databricks_metastore_data_access.main.name
}

output "storage_credential_name" {
  value = databricks_storage_credential.main.name
}

output "external_location_name" {
  value = databricks_external_location.main.name
}

output "external_location_url" {
  value = databricks_external_location.main.url
}
