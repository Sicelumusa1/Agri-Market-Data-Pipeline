import dlt
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class MarketDataPipeline:
    """Main pipeline orchestrator - supports both GCS and local sources"""
    
    def __init__(
        self, 
        source_type: str = "gcs",  # "gcs" or "local"
        bucket_name_or_dir: Optional[str] = None,
        dataset_name: str = "market_data",
        destination: str = "bigquery",  # Default to bigquery for cloud
        settings = None
    ):
        self.source_type = source_type.lower()
        self.bucket_name_or_dir = bucket_name_or_dir
        self.dataset_name = dataset_name
        self.destination = destination
        
        if self.source_type == "gcs":
            from .config.settings import get_settings
            self.settings = settings or get_settings()
            self.bucket_name = bucket_name_or_dir or self.settings.gcs_bucket_name
                
            logger.info(f"Initialized GCS MarketDataPipeline for bucket: {self.bucket_name}")
        else:
            self.settings = settings
            logger.info(f"Initialized Local MarketDataPipeline for directory: {bucket_name_or_dir}")
    
    def run_full_pipeline(
        self, 
        destination: Optional[str] = None,
        destination_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run complete pipeline for all file types"""
        dest = destination or self.destination
        logger.info(f"Starting {self.source_type} pipeline with destination: {dest}")
        start_time = datetime.utcnow()
        
        try:
            # Create appropriate source
            if self.source_type == "gcs":
                from .sources.file_based_source import FileBasedSource
                source = FileBasedSource(
                    bucket_name=self.bucket_name,
                    remove_non_analytics=getattr(self.settings, 'remove_non_analytics_fields', True)
                )
            else:  # local
                from .sources.local_file_source import LocalFileSource
                source = LocalFileSource(
                    base_dir=self.bucket_name_or_dir,
                    remove_non_analytics=True
                )
            
            # Configure destination with cloud-native settings
            dest_obj = self._configure_destination(dest, destination_config)
            dataset_name = self.dataset_name
            
            # Create dlt pipeline with state management
            pipeline_name = f"market_data_{self.source_type}_{dataset_name}"
            pipeline = dlt.pipeline(
                pipeline_name=pipeline_name,
                destination=dest_obj,
                dataset_name=dataset_name,
                # Enable state persistence for incremental loads
                pipeline_salt=os.getenv('DLT_PIPELINE_SALT', 'market-data-pipeline'),
            )
            
            # Run pipeline with progress tracking
            logger.info("Running dlt pipeline...")
            
            # Get data source
            data_source = source.get_data()
            
            # Apply incremental loading settings if needed
            load_info = pipeline.run(
                data_source,
                loader_file_format="parquet",  # Always use parquet for BigQuery
                write_disposition="merge" if self.source_type == "gcs" else "replace"
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Pipeline completed in {execution_time:.2f} seconds")
            
            # Return result with metadata
            result = {
                "status": "success",
                "load_info": str(load_info),
                "execution_time_seconds": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
                "source_type": self.source_type,
                "destination": dest,
                "dataset_name": dataset_name,
                "pipeline_name": pipeline_name,
                "loaded_packages": len(load_info.loads_ids) if hasattr(load_info, 'loads_ids') else 0
            }
            
            # Add table counts if available
            try:
                with pipeline.sql_client() as client:
                    result["table_counts"] = self._get_table_counts(client)
            except Exception as e:
                logger.warning(f"Could not get table counts: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": datetime.utcnow().isoformat(),
                "source_type": self.source_type,
                "destination": dest or self.destination
            }
    
    def _configure_destination(self, destination: str, config: Optional[Dict]):
        """Configure destination with cloud-native settings"""
        
        if destination == "bigquery":
            # BigQuery destination with automatic schema evolution
            destination_config = {
                "location": os.getenv('BIGQUERY_LOCATION', 'us-central1'),
                "has_legacy_engine": False,
            }
            if config:
                destination_config.update(config)
            
            # Use default credentials from environment
            return dlt.destinations.bigquery(**destination_config)
            
        elif destination == "duckdb":
            # DuckDB for local testing
            return dlt.destinations.duckdb(**config) if config else dlt.destinations.duckdb()
            
        elif destination == "postgres":
            # PostgreSQL destination (for alternative cloud)
            return dlt.destinations.postgres(**config) if config else dlt.destinations.postgres()
        
        else:
            return destination
    
    def run_by_data_type(
        self, 
        data_type: str,
        destination: Optional[str] = None,
        destination_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run pipeline for specific data type"""
        valid_types = ['summary', 'container', 'variety']
        if data_type not in valid_types:
            raise ValueError(f"data_type must be one of {valid_types}")
        
        dest = destination or self.destination
        logger.info(f"Starting {self.source_type} pipeline for data type: {data_type}")
        start_time = datetime.utcnow()
        
        try:
            # Create appropriate source
            if self.source_type == "gcs":
                from .sources.file_based_source import FileBasedSource
                source = FileBasedSource(
                    bucket_name=self.bucket_name,
                    remove_non_analytics=getattr(self.settings, 'remove_non_analytics_fields', True)
                )
            else:  # local
                from .sources.local_file_source import LocalFileSource
                source = LocalFileSource(
                    base_dir=self.bucket_name_or_dir,
                    remove_non_analytics=True
                )
            
            # Configure destination
            dest_obj = self._configure_destination(dest, destination_config)
            dataset_name = self.dataset_name
            
            pipeline = dlt.pipeline(
                pipeline_name=f"market_{data_type}_{self.source_type}_{dataset_name}",
                destination=dest_obj,
                dataset_name=dataset_name,
            )
            
            # Get appropriate data source
            if data_type == 'summary':
                data = source._get_summary_data()
            elif data_type == 'container':
                data = source._get_container_data()
            else:  # variety
                data = source._get_variety_data()
            
            load_info = pipeline.run(
                data,
                loader_file_format="parquet" if dest == "bigquery" else None
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"{data_type} pipeline completed in {execution_time:.2f} seconds")
            
            result = {
                "status": "success",
                "data_type": data_type,
                "load_info": str(load_info),
                "execution_time_seconds": execution_time,
                "source_type": self.source_type,
                "destination": dest,
                "dataset_name": dataset_name
            }
            
            return result
            
        except Exception as e:
            logger.error(f"{data_type} pipeline failed: {e}", exc_info=True)
            return {
                "status": "error",
                "data_type": data_type,
                "error": str(e),
                "source_type": self.source_type,
                "destination": dest
            }
    
    def _get_table_counts(self, client) -> Dict[str, int]:
        """Get row counts for each table"""
        tables = ["market_summary", "market_container", "market_variety"]
        counts = {}
        
        for table in tables:
            try:
                result = client.execute_sql(f"SELECT COUNT(*) FROM {self.dataset_name}.{table}")
                counts[table] = result[0][0] if result else 0
            except Exception as e:
                logger.warning(f"Could not get count for {table}: {e}")
                counts[table] = 0
        
        return counts