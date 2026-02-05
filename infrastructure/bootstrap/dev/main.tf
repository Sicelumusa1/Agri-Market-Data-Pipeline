
resource "google_storage_bucket" "tf_state" {
  name     = "${var.project_id}-tf-state"
  location = var.region

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }


  lifecycle {
    prevent_destroy = true
  }
}