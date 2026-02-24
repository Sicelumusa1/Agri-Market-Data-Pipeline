from pathlib import Path 
from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import os


class PipelineSettings(BaseSettings):
    """Pipeline configuration settings"""
    
    # ========== GCS Configuration ==========
    gcs_bucket_name: str
    gcs_folder_prefix: str = "joburg-market"  # Folder inside bucket
    
    # ========== GCP Configuration ==========
    gcp_project_id: str
    
    # ========== BigQuery Configuration ==========
    bigquery_dataset_name: str = "market_data"
    bigquery_location: str = "US"
    
    # ========== Pipeline Configuration ==========
    pipeline_source: str = "gcs"
    pipeline_destination: str = "bigquery"
    max_workers: int = 3
    chunk_size: int = 1000
    log_level: str = "INFO"
    enable_parallel_processing: bool = True
    remove_non_analytics_fields: bool = True
    
    # ========== Local Configuration ==========
    local_data_dir: str = "./data"
    
    class Config:
        env_file = Path(__file__).resolve().parents[2] / ".env" if os.path.exists(Path(__file__).resolve().parents[2] / ".env") else None
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> PipelineSettings:
    """Get cached settings instance"""
    return PipelineSettings()


def get_gcs_path(bucket: str = None, prefix: str = None, data_type: str = None) -> str:
    """
    Build GCS path for a specific data type.
    Example: my-data-bucket/joburg-market/summary
    """
    settings = get_settings()
    bucket_name = bucket or settings.gcs_bucket_name
    folder_prefix = prefix or settings.gcs_folder_prefix
    
    if data_type:
        return f"{bucket_name}/{folder_prefix}/{data_type}"
    return f"{bucket_name}/{folder_prefix}"