resource "google_service_account" "github_scraper" {
  account_id   = "github-scraper"
  display_name = "GitHub Actions Scraper SA"
}

resource "google_storage_bucket_iam_member" "bucket_writer" {
  bucket = google_storage_bucket.scraper_bucket.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.github_scraper.email}"
}

# Create a separate provider for the scraper repo
resource "google_iam_workload_identity_pool_provider" "github_scraper" {
  project = var.project_id
  
  # Reference the existing pool
  workload_identity_pool_id          = "github-pool"
  workload_identity_pool_provider_id = "github-scraper-provider"
  display_name                       = "GitHub Scraper Provider"
  
  attribute_condition = "assertion.repository == \"Sicelumusa1/market-data-ingestion-scraper\""
  
  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
  
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

# Then bind to provider
resource "google_service_account_iam_member" "wif_binding_scraper" {
  service_account_id = google_service_account.github_scraper.name
  role               = "roles/iam.workloadIdentityUser"
  
  # Use the correct numeric project ID
  member = "principalSet://iam.googleapis.com/projects/384931138677/locations/global/workloadIdentityPools/github-pool/attribute.repository/Sicelumusa1/market-data-ingestion-scraper"
}