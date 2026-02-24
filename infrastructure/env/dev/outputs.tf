output "scraper_bucket_name" {
  value = google_storage_bucket.scraper_bucket.name
}

output "github_scraper_sa_email" {
  value = google_service_account.github_scraper.email
}

output "kestra_ui_url" {
  description = "URL to access Kestra UI"
  value       = "https://${google_compute_address.kestra_vm.address}/ui"
}

output "kestra_api_url" {
  description = "Kestra API URL"
  value       = "https://${google_compute_address.kestra_vm.address}"
}

output "kestra_webhook_url" {
  description = "Webhook URL for triggering pipelines"
  value       = "https://${google_compute_address.kestra_vm.address}/api/v1/executions/webhook/agri-market/market-data-pipeline/${random_password.kestra_webhook_key.result}"
  sensitive   = true
}

output "kestra_db_connection" {
  description = "Cloud SQL connection name for Kestra"
  value       = google_sql_database_instance.kestra_db.connection_name
}



