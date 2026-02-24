import dlt
from dlt.sources.filesystem import filesystem, FileItemDict
from typing import Iterator, Optional
from ..utils.file_metadata_extractor import FileMetadataExtractor
from ..cleaners.summary_cleaner import SummaryCleaner
from ..cleaners.container_cleaner import ContainerCleaner
from ..cleaners.variety_cleaner import VarietyCleaner
import logging
from pandas.errors import EmptyDataError

logger = logging.getLogger(__name__)


class FileBasedSource:
    """Source that processes files from GCS bucket with folder structure using dlt filesystem"""
    
    def __init__(
        self,
        bucket_name: str,
        prefix: Optional[str] = None,
        remove_non_analytics: bool = True
    ):
        self.bucket_name = bucket_name
        self.prefix = prefix.rstrip("/") if prefix else None
        self.metadata_extractor = FileMetadataExtractor()
        self.summary_cleaner = SummaryCleaner(remove_non_analytics)
        self.container_cleaner = ContainerCleaner(remove_non_analytics)
        self.variety_cleaner = VarietyCleaner(remove_non_analytics)
        
        logger.info(f"Initialized source for bucket: {bucket_name}")
        if prefix:
            logger.info(f"With base prefix: {self.prefix}")
    
    def get_data(self):
        @dlt.source
        def get_all_data():
            """Get all data sources"""
            yield self._get_summary_data()
            yield self._get_container_data()
            yield self._get_variety_data()
        return get_all_data()
    
    def _get_filesystem_source(self, file_pattern: str, subfolder: str) -> filesystem:
        """Create a filesystem source for GCS with type-specific subfolder"""
        # Build the full GCS path with base prefix and subfolder
        if self.prefix:
            full_path = f"{self.prefix}/{subfolder}"
        else:
            full_path = subfolder
            
        bucket_url = f"gs://{self.bucket_name}/{full_path}"
        
        logger.info(f" GCS path: {bucket_url}")
        logger.info(f" Pattern: {file_pattern}")
        
        fs = filesystem(
            bucket_url=bucket_url,
            file_glob=file_pattern
        )
        
        # Try to peek at first item to see if any files are found
        try:
            import itertools
            first_item = next(itertools.islice(fs, 1), None)
            if first_item:
                logger.info(f" Found files in {subfolder}/")
            else:
                logger.warning(f" No files found in {subfolder}/ with pattern: {file_pattern}")
        except Exception as e:
            logger.error(f" Error accessing GCS path {bucket_url}: {e}")
        
        return fs
    
    def _process_file_item(self, file_item: FileItemDict, cleaner) -> Iterator[dict]:
        """Process a single file from the filesystem source"""
        import pandas as pd
        
        file_name = file_item["file_name"]
        file_metadata = self.metadata_extractor.extract(file_name)
        logger.info(f"Processing file: {file_name}")
        
        # Download the file content directly
        with file_item.open() as file_obj:
            try:
                # Read CSV from the file object
                df = pd.read_csv(file_obj)
                
                # Process each row
                row_count = 0
                for _, row in df.iterrows():
                    cleaned_row = cleaner.clean_row(row.to_dict(), file_metadata)
                    if cleaned_row:
                        logger.debug(f"YIELDING from _process_file_item: {cleaned_row}")
                        yield cleaned_row
                        row_count += 1
                
                logger.info(f"  → Extracted {row_count} rows from {file_name}")
            except EmptyDataError:
                logger.warning(f"  File {file_name} is empty, skipping")
            except Exception as e:
                logger.error(f"  Error processing {file_name}: {e}")
                raise
    
    def _get_summary_data(self):
        @dlt.resource(
            table_name="market_summary",
            write_disposition="merge",
            primary_key=["market", "commodity", "scrape_date"],
            columns={
                "value_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "value_sold_mtd": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "qty_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "qty_sold_mtd": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "kg_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "kg_sold_mtd": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "qty_available": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "scrape_date": {"data_type": "date", "nullable": False},
                "file_date": {"data_type": "date", "nullable": True},
            }
        )
        def summary_resource():
            pattern = "*_summary_*.csv"
            logger.info(f"Looking for summary files...")
            
            filesystem_source = self._get_filesystem_source(pattern, "summary")
            
            for file_item in filesystem_source:
                yield from self._process_file_item(file_item, self.summary_cleaner)
        
        return summary_resource
    
    def _get_container_data(self):
        @dlt.resource(
            table_name="market_container",
            write_disposition="merge",
            primary_key=["market", "commodity", "container_name", "scrape_date"],
            columns={
                "value_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "value_sold_mtd": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "qty_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "qty_sold_mtd": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "kg_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "kg_sold_mtd": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "qty_available": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "average_price_per_kg": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "scrape_date": {"data_type": "date", "nullable": False},
                "file_date": {"data_type": "date", "nullable": True},
            }
        )
        def container_resource():
            pattern = "*_container_*.csv"
            logger.info(f"Looking for container files...")
            
            filesystem_source = self._get_filesystem_source(pattern, "container")
            
            for file_item in filesystem_source:
                yield from self._process_file_item(file_item, self.container_cleaner)
        
        return container_resource
    
    def _get_variety_data(self):
        @dlt.resource(
            table_name="market_variety",
            write_disposition="merge",
            primary_key=["market", "commodity", "container_name", "variety", "scrape_date"],
            columns={
                "value_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "qty_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "kg_sold": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "average_price": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "highest_price": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "average_price_per_kg": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "highest_price_per_kg": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "unit_mass": {"data_type": "decimal", "precision": 15, "scale": 2, "nullable": True},
                "scrape_date": {"data_type": "date", "nullable": False},
                "file_date": {"data_type": "date", "nullable": True},
            }
        )
        def variety_resource():
            pattern = "*_variety_*.csv"
            logger.info(f"Looking for variety files...")
            
            filesystem_source = self._get_filesystem_source(pattern, "variety")
            
            for file_item in filesystem_source:
                yield from self._process_file_item(file_item, self.variety_cleaner)
        
        return variety_resource