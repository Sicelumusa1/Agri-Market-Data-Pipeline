resource "google_service_account" "github_scraper" {
  account_id   = "github-scraper-dev"
  display_name = "GitHub Actions Scraper SA - Dev"
}

resource "google_storage_bucket_iam_member" "bucket_writer" {
  bucket = google_storage_bucket.scraper_bucket.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.github_scraper.email}"
}

resource "google_iam_workload_identity_pool_provider" "github_scraper" {
  project = var.project_id

  workload_identity_pool_id          = "github-pool-dev"
  workload_identity_pool_provider_id = "github-scraper-provider-dev"
  display_name                       = "GitHub Scraper Provider - Dev"

  attribute_condition = "assertion.repository == \"Sicelumusa1/market-data-ingestion-scraper\""

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account_iam_member" "wif_binding_scraper" {
  service_account_id = google_service_account.github_scraper.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${var.workload_identity_pool_name}/attribute.repository/Sicelumusa1/market-data-ingestion-scraper"
}

resource "google_service_account" "runtime" {
  account_id   = "runtime-dev"
  display_name = "Cloud Run / Kestra Runtime (Dev)"
}

resource "google_service_account" "eventarc" {
  account_id   = "eventarc-dev"
  display_name = "Eventarc Trigger SA (Dev)"
}

resource "google_project_iam_member" "eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

resource "google_project_iam_member" "eventarc_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

resource "google_project_iam_member" "gcs_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:service-${var.project_number}@gs-project-accounts.iam.gserviceaccount.com"
}


# IAM RESOURCES - FOR KESTRA

# Eventarc invoker to use eventarc SA
resource "google_cloud_run_v2_service_iam_member" "eventarc_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.kestra.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.eventarc.email}"
}

#  Allow runtime SA to access Cloud SQL 
resource "google_project_iam_member" "runtime_cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow runtime SA to access Secret Manager
resource "google_project_iam_member" "runtime_secret_accessor" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

#  Allow runtime SA to access Kestra storage bucket
resource "google_project_iam_member" "kestra_storage_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_cloud_run_v2_service_iam_member" "kestra_ui_user" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.kestra.name

  role   = "roles/run.invoker"
  member = "user:${var.kestra_ui_user_email}"
}

