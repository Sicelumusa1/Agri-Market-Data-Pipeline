# Service account for GitHub Actions
resource "google_service_account" "github_pipeline" {
  account_id   = "github-pipeline"
  display_name = "GitHub Actions Pipeline SA"
}

# Workload Identity Pool
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github-pool"
  display_name              = "GitHub Actions Pool"
}

# Workload Identity Pool Provider
resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-provider"
  display_name                       = "GitHub Provider"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }

  attribute_mapping = {
    "google.subject"       = "assertion.sub"
    "attribute.repository" = "assertion.repository"
  }

  attribute_condition = "assertion.repository == \"Sicelumusa1/Agri-Market-Data-Pipeline\""
}

# Bind service account to WIF for pipeline repo
resource "google_service_account_iam_member" "wif_binding_pipeline" {
  service_account_id = google_service_account.github_pipeline.name
  role               = "roles/iam.workloadIdentityUser"
  member = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/Sicelumusa1/Agri-Market-Data-Pipeline"
}

# Grant the SA access to the Terraform backend bucket
resource "google_storage_bucket_iam_member" "terraform_sa" {
  bucket = "market-data-tf-state"
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github_pipeline.email}"
}

# Grant the SA access to manage storage buckets
resource "google_project_iam_member" "pipeline_storage_admin" {
  project = var.project_id
  role    = "roles/storage.admin"
  member  = "serviceAccount:${google_service_account.github_pipeline.email}"
}

# Grant the SA access to manage service accounts
resource "google_project_iam_member" "pipeline_sa_admin" {
  project = var.project_id
  role    = "roles/iam.serviceAccountAdmin"
  member  = "serviceAccount:${google_service_account.github_pipeline.email}"
}

# Grant the SA access to manage Workload Identity Pools
resource "google_project_iam_member" "pipeline_wif_admin" {
  project = var.project_id
  role    = "roles/iam.workloadIdentityPoolAdmin"
  member  = "serviceAccount:${google_service_account.github_pipeline.email}"
}
