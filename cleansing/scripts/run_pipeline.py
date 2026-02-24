import dlt
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os
import sys

logger = logging.getLogger(__name__)

class MarketDataPipeline:
    """Main pipeline orchestrator - supports both GCS and local sources"""
    
    def __init__(
        self,
        source_type: str = "gcs",
        bucket_name_or_dir: Optional[str] = None,
        bucket_prefix: Optional[str] = None,
        dataset_name: str = "market_data",
        destination: str = "bigquery",
        gcp_project: Optional[str] = None,
        remove_non_analytics: bool = True,
        settings=None
    ):
        self.source_type = source_type.lower()
        self.bucket_name_or_dir = bucket_name_or_dir
        self.bucket_prefix = bucket_prefix
        self.dataset_name = dataset_name
        self.destination = destination
        self.remove_non_analytics = remove_non_analytics

        # Only load settings if absolutely needed (e.g., for BigQuery location)
        self.settings = settings

        # Set GCP environment variables if provided
        if gcp_project:
            os.environ['GCP_PROJECT_ID'] = gcp_project
            os.environ['GOOGLE_CLOUD_PROJECT'] = gcp_project
            self.gcp_project = gcp_project
        else:
            self.gcp_project = None

        logger.info(f"Initialized MarketDataPipeline:")
        logger.info(f"  Source Type: {self.source_type}")
        logger.info(f"  Bucket/Directory: {self.bucket_name_or_dir}")
        if self.bucket_prefix:
            logger.info(f"  Prefix: {self.bucket_prefix}")
        logger.info(f"  Dataset: {self.dataset_name}")
        if self.gcp_project:
            logger.info(f"  GCP Project: {self.gcp_project}")

    def run_full_pipeline(self, destination: Optional[str] = None) -> Dict[str, Any]:
        """Run complete pipeline for all file types"""
        dest = destination or self.destination
        logger.info(f"Starting {self.source_type} pipeline with destination: {dest}")
        start_time = datetime.utcnow()
        
        try:
            # Choose source
            if self.source_type == "gcs":
                from dlt_project.sources.file_based_source import FileBasedSource
                source = FileBasedSource(
                    bucket_name=self.bucket_name_or_dir,
                    prefix=self.bucket_prefix,
                    remove_non_analytics=self.remove_non_analytics
                )
            else:
                from dlt_project.sources.local_file_source import LocalFileSource
                source = LocalFileSource(
                    base_dir=self.bucket_name_or_dir,
                    remove_non_analytics=self.remove_non_analytics
                )
            
            # Configure destination
            dest_obj = self._configure_destination(dest)
            
            # Create dlt pipeline
            pipeline = dlt.pipeline(
                pipeline_name=f"market_data_{self.source_type}",
                destination=dest_obj,
                dataset_name=self.dataset_name,
            )
            
            logger.info("Running dlt pipeline...")
            load_info = pipeline.run(
                source.get_data(),
                loader_file_format="parquet" if dest == "bigquery" else None
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "success",
                "load_info": str(load_info),
                "execution_time_seconds": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
                "source_type": self.source_type,
                "destination": dest,
                "dataset_name": self.dataset_name,
                "source_path": self.bucket_name_or_dir,
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "execution_time_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "timestamp": datetime.utcnow().isoformat(),
                "source_type": self.source_type,
                "destination": dest
            }
    
    def run_by_data_type(self, data_type: str, destination: Optional[str] = None) -> Dict[str, Any]:
        """Run pipeline for specific data type"""
        valid_types = ['summary', 'container', 'variety']
        if data_type not in valid_types:
            raise ValueError(f"data_type must be one of {valid_types}")
        
        dest = destination or self.destination
        logger.info(f"Starting {self.source_type} pipeline for data type: {data_type}")
        start_time = datetime.utcnow()
        
        try:
            # Choose source
            if self.source_type == "gcs":
                from dlt_project.sources.file_based_source import FileBasedSource
                source = FileBasedSource(
                    bucket_name=self.bucket_name_or_dir,
                    prefix=self.bucket_prefix,
                    remove_non_analytics=self.remove_non_analytics
                )
            else:
                from dlt_project.sources.local_file_source import LocalFileSource
                source = LocalFileSource(
                    base_dir=self.bucket_name_or_dir,
                    remove_non_analytics=self.remove_non_analytics
                )
            
            # Configure destination
            dest_obj = self._configure_destination(dest)
            
            pipeline = dlt.pipeline(
                pipeline_name=f"market_{data_type}_{self.source_type}",
                destination=dest_obj,
                dataset_name=self.dataset_name,
            )
            
            # Fetch data for this type
            data = {
                "summary": source._get_summary_data,
                "container": source._get_container_data,
                "variety": source._get_variety_data
            }[data_type]()
            
            load_info = pipeline.run(
                data,
                loader_file_format="parquet" if dest == "bigquery" else None
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return {
                "status": "success",
                "data_type": data_type,
                "load_info": str(load_info),
                "execution_time_seconds": execution_time,
                "source_type": self.source_type,
                "destination": dest,
                "dataset_name": self.dataset_name,
                "source_path": self.bucket_name_or_dir,
            }
            
        except Exception as e:
            logger.error(f"{data_type} pipeline failed: {e}", exc_info=True)
            return {
                "status": "error",
                "data_type": data_type,
                "error": str(e),
                "source_type": self.source_type,
                "destination": dest
            }
    
    def _configure_destination(self, destination: str):
        """Configure destination"""
        if destination == "bigquery":
            location = getattr(self.settings, 'bigquery_location', "us-central1") if self.settings else "us-central1"
            return dlt.destinations.bigquery(location=location)
        elif destination == "duckdb":
            return dlt.destinations.duckdb()
        elif destination == "postgres":
            return dlt.destinations.postgres()
        else:
            return destination

if __name__ == "__main__":
    import argparse

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Parse CLI arguments
    parser = argparse.ArgumentParser(description="Market Data Pipeline Runner")
    parser.add_argument("--type", required=True, choices=["summary", "container", "variety"],
                        help="Type of data to process")
    parser.add_argument("--source", default="gcs", choices=["gcs", "local"], help="Data source type")
    parser.add_argument("--bucket", help="GCS bucket or local folder")
    parser.add_argument("--prefix", help="GCS folder prefix")
    parser.add_argument("--destination", default="bigquery", help="Destination for pipeline")
    parser.add_argument("--dataset", default="market_data", help="BigQuery dataset name")
    parser.add_argument("--gcp-project", help="GCP project ID")
    parser.add_argument("--output-json", action="store_true", help="Output result as JSON")
    
    args = parser.parse_args()

    # Log environment for debugging
    logger.info(f"Starting pipeline for data type: {args.type}")
    logger.info(f"Source: {args.source}")
    logger.info(f"Bucket/Directory: {args.bucket}")
    logger.info(f"Prefix: {args.prefix}")
    logger.info(f"Destination: {args.destination}")
    logger.info(f"Dataset: {args.dataset}")
    logger.info(f"GCP Project: {args.gcp_project}")

    # Initialize pipeline
    pipeline = MarketDataPipeline(
        source_type=args.source,
        bucket_name_or_dir=args.bucket,
        bucket_prefix=args.prefix,
        dataset_name=args.dataset,
        gcp_project=args.gcp_project
    )

    # Run pipeline for the specified data type
    result = pipeline.run_by_data_type(args.type, destination=args.destination)

    # Print result
    print("\n=== Pipeline Execution Result ===")
    print(f"Status: {result['status']}")
    print(f"Execution time: {result.get('execution_time_seconds', 0):.2f} seconds")
    print(f"Data type: {result['data_type']}")
    if result['status'] == 'success':
        print(f"Load info: {result.get('load_info', 'N/A')}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

    # Exit with appropriate code for Cloud Run Job
    if result['status'] == 'error':
        sys.exit(1)