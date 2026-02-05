from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache

class PipelineSettings(BaseSettings):
    """Pipeline configuration settings"""
    
    # GCS Configuration
    gcs_bucket_name: str
    gcs_credentials_path: Optional[str] = None
    
    # BigQuery Configuration
    bigquery_project_id: str
    bigquery_dataset_name: str = "market_data"
    bigquery_location: str = "US"
    
    # Pipeline Configuration
    max_workers: int = 3
    chunk_size: int = 1000
    log_level: str = "INFO"
    enable_parallel_processing: bool = True
    
    # Data Processing
    remove_non_analytics_fields: bool = True
    validate_commodity_consistency: bool = True
    
    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False

@lru_cache()
def get_settings() -> PipelineSettings:
    """Get cached settings instance"""
    return PipelineSettings()