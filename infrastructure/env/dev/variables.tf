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

variable "bigquery_dataset_name" {
  type = string
}

variable "bigquery_location" {
  type    = string
  default = "us-central1"
}

variable "eventarc_sa_email" {
  type = string
}

variable "project_number" {
  type = string
}

variable "environment" {
  description = "Environment name (dev/prod)"
  type        = string
  default     = "dev"
}

variable "kestra_image" {
  type = string
}

variable "db_host" {
  type = string
}

variable "db_name" {
  type = string

}

variable "db_user" {
  type = string
}

variable "db_password" {
  type = string
}

variable "kestra_db_ip" {
  type = string
}

variable "kestra_ui_user_email" {
  type = string
}

variable "gemini_api_key" {
  description = "API key for Google Gemini"
  type        = string
  sensitive   = true
}

variable "gcs_prefix" {
  type = string
}