resource "google_service_account" "github_scraper" {
  account_id   = "github-scraper"
  display_name = "GitHub Actions Scraper SA"
}

resource "google_storage_bucket_iam_member" "bucket_writer" {
  bucket = google_storage_bucket.scraper_bucket.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.github_scraper.email}"
}

resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"

  display_name = "GitHub Provider"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }
}

resource "google_service_account_iam_member" "wif_binding" {
  service_account_id = google_service_account.github_scraper.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/Sicelumusa1/market-data-ingestion-scraper"
}

