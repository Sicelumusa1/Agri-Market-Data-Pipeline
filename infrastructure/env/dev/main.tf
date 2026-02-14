resource "google_bigquery_dataset" "market_data" {
  dataset_id = var.bigquery_dataset_name
  location   = var.bigquery_location
  project    = var.project_id

  labels = {
    env    = "dev"
    domain = "market-data"
    owner  = "platform"
  }
}

resource "google_artifact_registry_repository" "containers" {
  depends_on = [
    google_project_service.artifact_registry
  ]

  location      = var.region
  repository_id = "data-platform"
  description   = "Docker images for data platform workloads"
  format        = "DOCKER"
}

# KESTRA INFRASTRUCTURE

# Kestra Backend 
resource "google_sql_database_instance" "kestra_db" {
  name             = "kestra-db-${var.environment}"
  database_version = "POSTGRES_14"
  region           = var.region
  project          = var.project_id

  settings {
    tier              = "db-f1-micro"
    availability_type = "ZONAL"

    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      point_in_time_recovery_enabled = false
    }

    ip_configuration {
      ipv4_enabled = true
      authorized_networks {
        name  = "allow-cloud-run"
        value = "0.0.0.0/0"
      }
    }

    disk_size = 10
    disk_type = "PD_SSD"
  }

  deletion_protection = false
}

resource "google_sql_database" "kestra_db" {
  name     = "kestra"
  instance = google_sql_database_instance.kestra_db.name
  project  = var.project_id
}

resource "random_password" "kestra_db_password" {
  length  = 24
  special = false
}

resource "google_sql_user" "kestra_user" {
  name     = "kestra"
  instance = google_sql_database_instance.kestra_db.name
  password = random_password.kestra_db_password.result
  project  = var.project_id
}

# GCS Bucket for Kestra Storage
resource "google_storage_bucket" "kestra_storage" {
  name          = "${var.project_id}-kestra-storage-${var.environment}"
  location      = var.region
  storage_class = "STANDARD"
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }
}

# Secret Manager for Kestra credentials 
resource "random_password" "kestra_webhook_key" {
  length  = 32
  special = false
}

resource "google_secret_manager_secret" "kestra_webhook_key" {
  depends_on = [google_project_service.secretmanager]
  secret_id  = "kestra-webhook-key-${var.environment}"
  project    = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "kestra_webhook_key" {
  secret      = google_secret_manager_secret.kestra_webhook_key.id
  secret_data = random_password.kestra_webhook_key.result
}

resource "google_secret_manager_secret" "kestra_db_password" {
  depends_on = [google_project_service.secretmanager]
  secret_id  = "kestra-db-password-${var.environment}"
  project    = var.project_id

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_version" "kestra_db_password" {
  secret      = google_secret_manager_secret.kestra_db_password.id
  secret_data = random_password.kestra_db_password.result
}

# Kestra Cloud Run Service 
resource "google_cloud_run_v2_service" "kestra" {
  name     = "kestra-dev"
  location = var.region
  project  = var.project_id

  template {
    service_account = google_service_account.runtime.email

    containers {
      image = var.kestra_image
      args  = ["server", "standalone"]

      ports {
        container_port = 8080
      }

      env {
        name  = "KESTRA_CONFIGURATION"
        value = <<-EOT
          datasources:
            default:
              url: jdbc:postgresql://${var.kestra_db_ip}:5432/kestra
              driverClassName: org.postgresql.Driver
              username: kestra
              password: ${random_password.kestra_db_password.result}

          kestra:
            repository:
              type: postgres
            queue:
              type: postgres
            storage:
              type: gcs
              gcs:
                bucket: ${google_storage_bucket.kestra_storage.name}

          server:
            address: 0.0.0.0
            port: 8080
          EOT
      }

      # JVM options
      env {
        name  = "JAVA_OPTS"
        value = "-Xms512m -Xmx2g -XX:+UseG1GC"
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
        cpu_idle = false
      }

      startup_probe {
        http_get {
          path = "/health"
          port = 8081
        }
        initial_delay_seconds = 60
        timeout_seconds       = 10
        period_seconds        = 10
        failure_threshold     = 20
      }
    }

    scaling {
      min_instance_count = 1
      max_instance_count = 1
    }

    timeout = "900s"

    annotations = {
      "run.googleapis.com/execution-environment" = "gen2"
      "run.googleapis.com/startup-cpu-boost"     = "true"
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }
}


# Eventarc Trigger 
resource "google_eventarc_trigger" "kestra_trigger" {
  depends_on = [
    google_project_service.eventarc,
    google_cloud_run_v2_service.kestra
  ]

  name     = "kestra-trigger-${var.environment}"
  location = var.region
  project  = var.project_id

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }

  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.scraper_bucket.name
  }


  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.kestra.name
      region  = var.region
      # Add webhook path
      path = "/api/v1/executions/webhook/agri-market/market-data-pipeline/${random_password.kestra_webhook_key.result}"
    }
  }

  service_account = google_service_account.eventarc.email

  # Force recreation when Kestra service changes
  lifecycle {
    replace_triggered_by = [
      google_cloud_run_v2_service.kestra
    ]
  }
}


resource "google_project_service" "artifact_registry" {
  project            = var.project_id
  service            = "artifactregistry.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "cloud_run" {
  project            = var.project_id
  service            = "run.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "eventarc" {
  project            = var.project_id
  service            = "eventarc.googleapis.com"
  disable_on_destroy = false
}

resource "google_project_service" "iam" {
  project            = var.project_id
  service            = "iam.googleapis.com"
  disable_on_destroy = false
}

# Enable Cloud SQL Admin API ---
resource "google_project_service" "cloudsql" {
  project            = var.project_id
  service            = "sqladmin.googleapis.com"
  disable_on_destroy = false
}

# Enable Secret Manager API ---
resource "google_project_service" "secretmanager" {
  project            = var.project_id
  service            = "secretmanager.googleapis.com"
  disable_on_destroy = false
}

