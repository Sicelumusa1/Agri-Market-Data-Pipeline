#!/usr/bin/env python3
"""
Local testing pipeline runner for GCS-like folder structure.
"""
import argparse
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dlt_project.sources.local_file_source import LocalFileSource
from dlt_project.pipeline import MarketDataPipeline

def setup_logging(log_level: str = "INFO"):
    """Configure logging"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )

def find_data_directory(user_path: str = None) -> Path:
    """Find the data directory, with user path as priority"""
    if user_path:
        path = Path(user_path)
        if path.exists():
            return path.resolve()
    
    # Default paths to try
    default_paths = [
        Path("/home/scelumusa/Documents/market-data-ingestion-scraper/data"),
        Path("../market-data-ingestion-scraper/data"),
        Path("market-data-ingestion-scraper/data"),
        Path("./data"),
    ]
    
    for path in default_paths:
        if path.exists():
            return path.resolve()
    
    return None

def validate_data_directory(data_dir: Path) -> bool:
    """Validate that data directory has the expected structure"""
    logger = logging.getLogger(__name__)
    
    if not data_dir.exists():
        logger.error(f"Data directory does not exist: {data_dir}")
        return False
    
    # Check for GCS-like structure
    has_subfolders = all([
        (data_dir / "summary").exists(),
        (data_dir / "container").exists(), 
        (data_dir / "variety").exists()
    ])
    
    if has_subfolders:
        logger.info("Detected GCS-like folder structure (summary/, container/, variety/)")
        
        # Check each folder for CSV files
        total_files = 0
        for folder in ["summary", "container", "variety"]:
            folder_path = data_dir / folder
            csv_files = list(folder_path.glob("*.csv"))
            logger.info(f"  {folder}/: {len(csv_files)} CSV files")
            total_files += len(csv_files)
            
            if csv_files:
                # Show first few filenames
                for f in csv_files[:2]:
                    logger.debug(f"    - {f.name}")
                if len(csv_files) > 2:
                    logger.debug(f"    ... and {len(csv_files) - 2} more")
            else:
                logger.warning(f"  {folder}/: No CSV files found")
        
        logger.info(f"Total files: {total_files}")
        return True
    else:
        # Check for flat structure
        csv_files = list(data_dir.glob("*.csv"))
        if csv_files:
            logger.info(f"Detected flat folder structure: {len(csv_files)} CSV files")
            return True
        else:
            logger.error("No CSV files found in data directory")
            return False

def main():
    parser = argparse.ArgumentParser(description="Local Market Data Pipeline Test")
    parser.add_argument(
        "--data-dir",
        help="Directory containing data (default: auto-detected)"
    )
    parser.add_argument(
        "--duckdb-path",
        default=":memory:",
        help="DuckDB database path (default: :memory: for in-memory)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit processing to N files per type (for quick testing)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    # Find data directory
    data_dir = find_data_directory(args.data_dir)
    
    if not data_dir:
        logger.error("Could not find data directory.")
        logger.info("Please specify the correct path with --data-dir")
        logger.info("   Example: --data-dir /home/scelumusa/Documents/market-data-ingestion-scraper/data")
        sys.exit(1)
    
    logger.info(f"Using data directory: {data_dir}")
    
    if not validate_data_directory(data_dir):
        sys.exit(1)
    
    try:
        # Initialize pipeline with local source
        pipeline = MarketDataPipeline(
            source_type="local",
            bucket_name_or_dir=str(data_dir)
        )
        
        # Configure DuckDB destination
        duckdb_config = {
            "database": args.duckdb_path,
        }
        
        # Run pipeline
        logger.info(" Starting local pipeline with DuckDB destination...")
        result = pipeline.run_full_pipeline(
            destination="duckdb",
            destination_config=duckdb_config
        )
        
        # Print results
        print("\n" + "="*80)
        print("PIPELINE RESULTS")
        print("="*80)
        
        if result["status"] == "success":
            print(" Pipeline completed successfully!")
            print(f"  Execution time: {result['execution_time_seconds']:.2f} seconds")
            
            if "table_counts" in result:
                print("\n Table Row Counts:")
                total_rows = 0
                for table, count in result["table_counts"].items():
                    print(f"  - {table}: {count:,} rows")
                    total_rows += count
                print(f"   Total: {total_rows:,} rows")
            
            if "sample_data" in result:
                print("\n Sample Data (first row from each table):")
                for table, rows in result["sample_data"].items():
                    if rows:
                        print(f"\n{table}:")
                        if rows and len(rows) > 0:
                            # Get column names
                            with pipeline._get_sql_client() as client:
                                try:
                                    col_result = client.execute_sql(f"PRAGMA table_info({table})")
                                    if col_result:
                                        columns = [col[1] for col in col_result]
                                        # Show first row with column names (limit to 5 columns)
                                        for col_name, value in zip(columns[:5], rows[0][:5]):
                                            print(f"  {col_name}: {value}")
                                        if len(columns) > 5 or len(rows[0]) > 5:
                                            print(f"  ... and {max(len(columns), len(rows[0])) - 5} more columns")
                                except:
                                    # Fallback: show raw row (first 5 values)
                                    print(f"  {rows[0][:5]}")
                                    if len(rows[0]) > 5:
                                        print(f"  ... and {len(rows[0]) - 5} more values")
            
            print(f"\n Source: {data_dir} (local)")
            print(f"  Destination: DuckDB ({args.duckdb_path})")
            
            # Save to file if not in-memory
            if args.duckdb_path != ":memory:":
                print(f"\n Data saved to: {args.duckdb_path}")
                print("   You can query it with:")
                print(f"   duckdb {args.duckdb_path}")
                print("   Or in Python:")
                print(f'   import duckdb; conn = duckdb.connect("{args.duckdb_path}")')
                
        else:
            print(f" Pipeline failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()