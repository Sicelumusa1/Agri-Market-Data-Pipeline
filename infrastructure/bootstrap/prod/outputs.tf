output "state_bucket_name" {
  description = "Name of the Terraform state bucket"
  value       = google_storage_bucket.tf_state.name
}

output "workload_identity_pool_name" {
  description = "Full resource name of the workload identity pool"
  value       = google_iam_workload_identity_pool.github.name
}

output "workload_identity_pool_id" {
  description = "ID of the workload identity pool"
  value       = google_iam_workload_identity_pool.github.workload_identity_pool_id
}

output "workload_identity_provider_name" {
  description = "Full resource name of the workload identity provider"
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "workload_identity_provider_id" {
  description = "ID of the workload identity provider"
  value       = google_iam_workload_identity_pool_provider.github.workload_identity_pool_provider_id
}

output "github_actions_service_account_email" {
  description = "Email of the GitHub Actions service account"
  value       = google_service_account.github_actions.email
}

output "github_actions_service_account_name" {
  description = "Full resource name of the GitHub Actions service account"
  value       = google_service_account.github_actions.name
}