output "scraper_bucket_name" {
  value = google_storage_bucket.scraper_bucket.name
}

output "github_scraper_sa_email" {
  value = google_service_account.github_scraper.email
}