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

# Enable Compute Engine API
resource "google_project_service" "compute" {
  project = var.project_id
  service = "compute.googleapis.com"

  # Don't disable the API when this resource is destroyed
  disable_on_destroy = false
}

# Static IP for Kestra VM
resource "google_compute_address" "kestra_vm" {
  name   = "kestra-vm-ip"
  region = var.region
}

# Firewall rule to allow HTTP/HTTPS traffic to Kestra VM

resource "google_compute_firewall" "kestra_vm" {
  name    = "kestra-vm-firewall"
  network = "default"

  allow {
    protocol = "tcp"
    ports    = ["443", "22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["kestra-vm"]
  depends_on = [
    google_project_service.compute,
  ]
}

resource "google_compute_instance" "kestra" {
  name         = "kestra-dev-vm"
  machine_type = "e2-standard-2"
  zone         = "${var.region}-a"
  project      = var.project_id

  tags = ["kestra-vm"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 50
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.kestra_vm.address
    }
  }

  metadata_startup_script = <<-EOF
    #!/bin/bash
    set -e
    
    # Update system
    apt-get update
    apt-get upgrade -y
    
    # Install Docker
    apt-get install -y docker.io
    systemctl enable docker
    systemctl start docker
    
    # Install Docker Compose
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Install Nginx
    apt-get install -y nginx
    
    # Create self-signed SSL certificate (for testing/POC)
    mkdir -p /etc/nginx/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/nginx/ssl/kestra.key \
      -out /etc/nginx/ssl/kestra.crt \
      -subj "/C=US/ST=State/L=City/O=Organization/CN=${google_compute_address.kestra_vm.address}"
    
    # Configure Nginx as reverse proxy with SSL
    cat > /etc/nginx/sites-available/kestra <<'NGINX'
    server {
        listen 443 ssl;
        server_name ${google_compute_address.kestra_vm.address};
        
        ssl_certificate /etc/nginx/ssl/kestra.crt;
        ssl_certificate_key /etc/nginx/ssl/kestra.key;
        
        # SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        
        # Logging
        access_log /var/log/nginx/kestra-access.log;
        error_log /var/log/nginx/kestra-error.log;
        
        location / {
            # Forward requests to Kestra running on HTTP
            proxy_pass http://127.0.0.1:8080;
            
            # Preserve original host and client IP
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # WebSocket support (if needed)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
    
    # Optional: Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name ${google_compute_address.kestra_vm.address};
        return 301 https://$server_name$request_uri;
    }
    NGINX
    
    # Enable the site
    ln -sf /etc/nginx/sites-available/kestra /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    nginx -t
    
    # Restart Nginx
    systemctl restart nginx
    
    # Create Kestra directory
    mkdir -p /opt/kestra
    cd /opt/kestra
    
    # Create docker-compose.yml
    cat > docker-compose.yml <<'YAML'
    services:
      kestra:
        image: us-central1-docker.pkg.dev/${var.project_id}/data-platform/kestra:0.18.5
        container_name: kestra
        ports:
          - "127.0.0.1:8080:8080"
          - "8081:8081"
        environment:
          - KESTRA_CONFIGURATION=
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
              ai:
                enabled: true
                type: gemini
                gemini:
                  api-key: "${var.gemini_api_key}"
                  model-name: "gemini-2.5-flash"
                  endpoint: "https://generativelanguage.googleapis.com/v1beta"
            server:
              address: 0.0.0.0
              port: 8080
          - JAVA_OPTS=-Xms512m -Xmx2g -XX:+UseG1GC
          - SECRET_GCP_PROJECT_ID=${base64encode(var.project_id)}
          - SECRET_KESTRA_WEBHOOK_KEY=${base64encode(random_password.kestra_webhook_key.result)}
          - SECRET_KESTRA_DB_PASSWORD=${base64encode(random_password.kestra_db_password.result)}
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock
          - /tmp:/tmp
        restart: always
        network_mode: host
    YAML
    
    # Start Kestra
    docker-compose up -d
    
    # Wait for Kestra to start
    sleep 30
    
    # Test Kestra is responding locally
    curl -f http://localhost:8080/api/v1/ping || echo "Kestra not responding"
    
    # Test Nginx can reach Kestra
    curl -f -k https://localhost/api/v1/ping || echo "Nginx cannot reach Kestra"
  EOF

  service_account {
    email  = google_service_account.runtime.email
    scopes = ["cloud-platform"]
  }

  depends_on = [
    google_project_service.compute,
    google_compute_address.kestra_vm,
    google_compute_firewall.kestra_vm,
    google_storage_bucket.kestra_storage,
    random_password.kestra_db_password,
    random_password.kestra_webhook_key
  ]
}

# Get project number
data "google_project" "current" {}

# Get the VPC network
data "google_compute_network" "default" {
  name    = "default"
  project = var.project_id
}

# Get the subnet
data "google_compute_subnetwork" "default" {
  name    = "default"
  region  = var.region
  project = var.project_id
}

# Create network attachment for Eventarc
resource "google_compute_network_attachment" "eventarc" {
  name        = "eventarc-network-attachment"
  region      = var.region
  project     = var.project_id
  description = "Network attachment for Eventarc to reach Kestra VM"

  subnetworks = [data.google_compute_subnetwork.default.self_link]

  connection_preference = "ACCEPT_AUTOMATIC"
}


resource "google_eventarc_trigger" "kestra_trigger" {
  name     = "kestra-trigger-dev"
  location = var.region
  project  = var.project_id

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.audit.log.v1.written"
  }

  matching_criteria {
    attribute = "serviceName"
    value     = "storage.googleapis.com"
  }

  matching_criteria {
    attribute = "methodName"
    value     = "storage.objects.create"
  }

  matching_criteria {
    attribute = "resourceName"
    value     = "projects/_/buckets/${google_storage_bucket.scraper_bucket.name}/objects/${var.gcs_prefix}/UPLOAD_DONE"
  }

  destination {
    http_endpoint {
      uri = "https://${google_compute_address.kestra_vm.address}:443/api/v1/executions/webhook/agri-market/market-data-pipeline/${random_password.kestra_webhook_key.result}"
    }

    # network_config is required for audit log triggers
    network_config {
      network_attachment = google_compute_network_attachment.eventarc.id
    }
  }

  service_account = google_service_account.eventarc.email
}
# Cloud Run Job for dlt pipeline
resource "google_cloud_run_v2_job" "dlt_pipeline" {
  name     = "dlt-pipeline-job"
  location = var.region
  project  = var.project_id

  template {
    template {
      containers {
        # Your dlt pipeline image
        image = "us-central1-docker.pkg.dev/${var.project_id}/data-platform/dlt-pipeline:001"

        # Environment variables that can be overridden
        env {
          name  = "source_type"
          value = "gcs"
        }
        env {
          name  = "gcp_project_id"
          value = var.project_id
        }
        env {
          name  = "gcs_bucket_name"
          value = var.bucket_name
        }
        env {
          name  = "gcs_folder_prefix"
          value = var.gcs_prefix
        }
        env {
          name  = "bigquery_dataset_name"
          value = var.bigquery_dataset_name
        }

        # Resource limits 
        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }
      }

      # Service account
      service_account = google_service_account.runtime.email

      # Retry and timeout 
      max_retries = 3
      timeout     = "3600s"
    }

    # Task count
    task_count = 1
  }

  depends_on = [
    google_artifact_registry_repository.containers,
    google_service_account.runtime
  ]
}

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

