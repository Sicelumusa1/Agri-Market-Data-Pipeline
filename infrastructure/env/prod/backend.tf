terraform {
  backend "gcs" {
    bucket = "agri-market-intelligence-prod-tf-state"
    prefix = "prod"
  }
}