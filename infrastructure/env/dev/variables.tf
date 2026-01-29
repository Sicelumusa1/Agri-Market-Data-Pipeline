variable "project_id" {}
variable "region" {
  default = "us-central1"
}

variable "bucket_name" {}

variable "workload_identity_pool_name" {
  description = "Full resource name of the workload identity pool"
  type        = string
  default     = "projects/1059980658833/locations/global/workloadIdentityPools/github-pool-dev"
}