output "scraper_bucket_name" {
  value = google_storage_bucket.scraper_bucket.name
}

output "github_scraper_sa_email" {
  value = google_service_account.github_scraper.email
}


# FOR KESTRA

output "kestra_ui_url" {
  description = "Kestra UI URL - access the Kestra dashboard"
  value       = "${google_cloud_run_v2_service.kestra.uri}/ui"
}

output "kestra_webhook_url" {
  description = "Webhook URL for UPLOAD_DONE trigger"
  value       = "https://${google_cloud_run_v2_service.kestra.uri}/api/v1/executions/webhook/agri-market/market-data-pipeline/${random_password.kestra_webhook_key.result}"
  sensitive   = true
}

output "kestra_api_url" {
  description = "Kestra API URL"
  value       = google_cloud_run_v2_service.kestra.uri
}

output "kestra_db_connection" {
  description = "Cloud SQL connection name for Kestra"
  value       = google_sql_database_instance.kestra_db.connection_name
}



