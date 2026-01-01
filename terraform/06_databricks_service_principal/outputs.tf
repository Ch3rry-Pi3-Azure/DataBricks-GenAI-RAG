output "service_principal_id" {
  value = databricks_service_principal.main.id
}

output "service_principal_application_id" {
  value = databricks_service_principal.main.application_id
}

output "service_principal_display_name" {
  value = databricks_service_principal.main.display_name
}
