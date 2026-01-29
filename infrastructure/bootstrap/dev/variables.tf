variable "project_id" {
  description = "The GCP project ID"
  type        = string
  default     = "agri-market-intelligence-dev"
}

variable "region" {
  description = "The GCP region"
  type        = string
  default     = "us-central1"
}

variable "github_owner" {
  description = "GitHub repository owner"
  type        = string
  default     = "Sicelumusa1"
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
  default     = "Agri-Market-Data-Pipeline"
}