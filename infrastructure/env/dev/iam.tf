# GitHub Scraper Service Account - Used by GitHub Actions to upload data to GCS
resource "google_service_account" "github_scraper" {
  account_id   = "github-scraper-dev"
  display_name = "GitHub Actions Scraper SA - Dev"
}

# Allow GitHub scraper SA to write objects to the scraper bucket
resource "google_storage_bucket_iam_member" "bucket_writer" {
  bucket = google_storage_bucket.scraper_bucket.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.github_scraper.email}"
}

# Workload Identity Pool Provider - Allows GitHub Actions to authenticate to GCP using the GitHub Scraper Service Account
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

# Bind the GitHub scraper service account to the workload identity pool
resource "google_service_account_iam_member" "wif_binding_scraper" {
  service_account_id = google_service_account.github_scraper.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${var.workload_identity_pool_name}/attribute.repository/Sicelumusa1/market-data-ingestion-scraper"
}

# Runtime Service Account - Used by Kestra Cloud Run service to access GCP resources
resource "google_service_account" "runtime" {
  account_id   = "runtime-dev"
  display_name = "Cloud Run / Kestra Runtime (Dev)"
  project      = var.project_id
}

# For Cloud Run Task Runner
resource "google_project_iam_member" "runtime_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow runtime SA to act as itself
resource "google_service_account_iam_member" "runtime_self_user" {
  service_account_id = google_service_account.runtime.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.runtime.email}"
}

# View logs for Cloud Run Jobs
resource "google_project_iam_member" "runtime_log_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Eventarc Service Account - Used by Eventarc to trigger Cloud Run
resource "google_service_account" "eventarc" {
  account_id   = "eventarc-dev"
  display_name = "Eventarc Trigger SA (Dev)"
  project      = var.project_id
}

# Allow Eventarc SA to receive events
resource "google_project_iam_member" "eventarc_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

#Allow Eventarc SA to invoke Cloud Run
resource "google_project_iam_member" "eventarc_run_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc.email}"
}

# IAM RESOURCES - FOR KESTRA

# Allow runtime SA to access Cloud SQL (for Kestra backend)
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

# Allow runtime SA to read/write to Kestra storage bucket
resource "google_storage_bucket_iam_member" "kestra_storage_admin" {
  bucket = google_storage_bucket.kestra_storage.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow runtime SA to read from/write to the scraper bucket (for data processing)
resource "google_storage_bucket_iam_member" "runtime_scraper_bucket_reader" {
  bucket = google_storage_bucket.scraper_bucket.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_storage_bucket_iam_member" "runtime_scraper_bucket_writer" {
  bucket = google_storage_bucket.scraper_bucket.name
  role   = "roles/storage.objectCreator"
  member = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow runtime SA to write to BigQuery (for data loading)
resource "google_project_iam_member" "runtime_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow runtime SA to create/update BigQuery jobs
resource "google_project_iam_member" "runtime_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow runtime SA to pull images from Artifact Registry
resource "google_project_iam_member" "runtime_artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow VM to access metadata and use service account
resource "google_project_iam_member" "runtime_iam_service_account_user" {
  project = var.project_id
  role    = "roles/iam.serviceAccountUser"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow VM to create and manage Cloud Run Jobs
resource "google_project_iam_member" "runtime_run_admin" {
  project = var.project_id
  role    = "roles/run.admin"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow VM to pull images 
resource "google_project_iam_member" "runtime_artifact_registry_puller" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}


# Enable Data Access audit logs for GCS (to capture UPLOAD_DONE events)
resource "google_project_iam_audit_config" "gcs_audit" {
  project = var.project_id
  service = "storage.googleapis.com"

  audit_log_config {
    log_type = "DATA_WRITE"
  }
}


# Allow runtime SA to publish metrics to Cloud Monitoring
resource "google_project_iam_member" "runtime_metric_writer" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

# Allow runtime SA to create logs
resource "google_project_iam_member" "runtime_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}


# Service Account for dbt Cloud

resource "google_service_account" "dbt_cloud_sa" {
  account_id   = "dbt-cloud-sa"
  display_name = "dbt Cloud Service Account"
  description  = "Service account used by dbt Cloud to run BigQuery transformations"
}


# BigQuery Data Viewer
resource "google_project_iam_member" "dbt_bigquery_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.dbt_cloud_sa.email}"
}

# BigQuery Data Editor
resource "google_project_iam_member" "dbt_bigquery_data_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.dbt_cloud_sa.email}"
}

# BigQuery Job User
resource "google_project_iam_member" "dbt_bigquery_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.dbt_cloud_sa.email}"
}


# BigQuery API
resource "google_project_service" "bigquery_api" {
  project = var.project_id
  service = "bigquery.googleapis.com"

  disable_on_destroy = false
}

# BigQuery Storage API
resource "google_project_service" "bigquery_storage_api" {
  project = var.project_id
  service = "bigquerystorage.googleapis.com"

  disable_on_destroy = false
}

# IAM API 
resource "google_project_service" "iam_api" {
  project = var.project_id
  service = "iam.googleapis.com"

  disable_on_destroy = false
}

# BigQuery Read Session User (Required for Storage API)
resource "google_project_iam_member" "dbt_bigquery_read_session_user" {
  project = var.project_id
  role    = "roles/bigquery.readSessionUser"
  member  = "serviceAccount:${google_service_account.dbt_cloud_sa.email}"
}