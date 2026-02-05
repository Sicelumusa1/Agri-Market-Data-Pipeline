terraform {
  backend "gcs" {
    bucket = "agri-market-intelligence-dev-tf-state"
    prefix = "dev"
  }
}