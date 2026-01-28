terraform {
  backend "gcs" {
    bucket = "market-data-tf-state"
    prefix = "infra"
  }
}
