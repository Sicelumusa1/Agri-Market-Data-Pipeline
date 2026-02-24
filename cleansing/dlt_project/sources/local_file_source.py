import dlt
import os
import pandas as pd
from typing import Iterator, Dict, Any, List, Optional
import logging
from pathlib import Path
from ..utils.file_metadata_extractor import FileMetadataExtractor
from ..cleaners.summary_cleaner import SummaryCleaner
from ..cleaners.container_cleaner import ContainerCleaner
from ..cleaners.variety_cleaner import VarietyCleaner

logger = logging.getLogger(__name__)

class LocalFileSource:
    """
    Source that processes local files with GCS-like folder structure.
    Expects: data/{summary,container,variety}/*.csv
    """
    
    def __init__(
        self, 
        base_dir: str, 
        remove_non_analytics: bool = True,
        folder_structure: str = "flat"  # "flat" or "gcs" (with subfolders)
    ):
        self.base_dir = Path(base_dir)
        self.folder_structure = folder_structure
        self.metadata_extractor = FileMetadataExtractor()
        self.summary_cleaner = SummaryCleaner(remove_non_analytics)
        self.container_cleaner = ContainerCleaner(remove_non_analytics)
        self.variety_cleaner = VarietyCleaner(remove_non_analytics)
        logger.info(f"Initialized LocalFileSource for directory: {base_dir} ({folder_structure} structure)")
    
    def get_data(self):
        @dlt.source
        def local_market_data():
            yield self._get_summary_data()
            yield self._get_container_data()
            yield self._get_variety_data()

        return local_market_data()
    
    def _get_summary_data(self):
        @dlt.resource(
            table_name="market_summary",
            write_disposition="replace",
            primary_key=["market", "commodity", "scrape_date"],
        )
        def summary_resource():
            if self.folder_structure == "gcs":
                # Look in summary/ subdirectory
                pattern = "summary/*_summary_*.csv"
                base_path = self.base_dir
            else:
                # Flat structure
                pattern = "*_summary_*.csv"
                base_path = self.base_dir
            
            logger.info(f"Looking for summary files with pattern: {pattern}")
            
            for filepath in self._find_local_files(base_path, pattern):
                file_metadata = self.metadata_extractor.extract(filepath.name)
                logger.info(f"Processing local file: {filepath}")
                
                try:
                    df = pd.read_csv(filepath)
                    for _, row in df.iterrows():
                        cleaned_row = self.summary_cleaner.clean_row(row.to_dict(), file_metadata)
                        if cleaned_row:
                            yield cleaned_row
                except Exception as e:
                    logger.error(f"Error reading file {filepath}: {e}")
                    continue
        
        return summary_resource
    
    def _get_container_data(self):
        @dlt.resource(
            table_name="market_container",
            write_disposition="replace",
            primary_key=["market", "commodity", "container_name", "scrape_date"],
        )
        def container_resource():
            if self.folder_structure == "gcs":
                pattern = "container/*_container_*.csv"
                base_path = self.base_dir
            else:
                pattern = "*_container_*.csv"
                base_path = self.base_dir
            
            logger.info(f"Looking for container files with pattern: {pattern}")
            
            for filepath in self._find_local_files(base_path, pattern):
                file_metadata = self.metadata_extractor.extract(filepath.name)
                logger.info(f"Processing local file: {filepath}")
                
                try:
                    df = pd.read_csv(filepath)
                    for _, row in df.iterrows():
                        cleaned_row = self.container_cleaner.clean_row(row.to_dict(), file_metadata)
                        if cleaned_row:
                            yield cleaned_row
                except Exception as e:
                    logger.error(f"Error reading file {filepath}: {e}")
                    continue
        
        return container_resource
    
    def _get_variety_data(self):
        @dlt.resource(
            table_name="market_variety",
            write_disposition="replace",
            primary_key=["market", "commodity", "container_name", "variety", "scrape_date"],
        )
        def variety_resource():
            if self.folder_structure == "gcs":
                pattern = "variety/*_variety_*.csv"
                base_path = self.base_dir
            else:
                pattern = "*_variety_*.csv"
                base_path = self.base_dir
            
            logger.info(f"Looking for variety files with pattern: {pattern}")
            
            for filepath in self._find_local_files(base_path, pattern):
                file_metadata = self.metadata_extractor.extract(filepath.name)
                logger.info(f"Processing local file: {filepath}")
                
                try:
                    df = pd.read_csv(filepath)
                    for _, row in df.iterrows():
                        cleaned_row = self.variety_cleaner.clean_row(row.to_dict(), file_metadata)
                        if cleaned_row:
                            yield cleaned_row
                except Exception as e:
                    logger.error(f"Error reading file {filepath}: {e}")
                    continue
        
        return variety_resource
    
    def _find_local_files(self, base_path: Path, pattern: str) -> List[Path]:
        """Find local files matching pattern with support for subdirectories"""
        import fnmatch
        
        files = []
        
        # If pattern has directory separator, handle accordingly
        if '/' in pattern:
            dir_part, file_pattern = pattern.split('/', 1)
            search_dir = base_path / dir_part
            if not search_dir.exists():
                logger.warning(f"Directory does not exist: {search_dir}")
                return files
            
            for filepath in search_dir.glob(file_pattern):
                if filepath.is_file():
                    files.append(filepath)
        else:
            # Search recursively in base directory
            for filepath in base_path.rglob(pattern):
                if filepath.is_file():
                    files.append(filepath)
        
        logger.info(f"Found {len(files)} files matching '{pattern}'")
        return files
    
    def validate_structure(self) -> Dict[str, List[str]]:
        """Validate the local folder structure and return found files"""
        validation = {
            "summary_files": [],
            "container_files": [],
            "variety_files": [],
            "issues": []
        }
        
        # Check for GCS-like structure
        if (self.base_dir / "summary").exists() and (self.base_dir / "container").exists() and (self.base_dir / "variety").exists():
            self.folder_structure = "gcs"
            logger.info("Detected GCS-like folder structure")
            
            # Find files in each subdirectory
            for folder, file_type in [("summary", "summary"), ("container", "container"), ("variety", "variety")]:
                folder_path = self.base_dir / folder
                if folder_path.exists():
                    pattern = f"*_{file_type}_*.csv"
                    files = list(folder_path.glob(pattern))
                    validation[f"{file_type}_files"] = [f.name for f in files]
                    logger.info(f"Found {len(files)} {file_type} files in {folder}/")
                else:
                    validation["issues"].append(f"Missing folder: {folder}")
        else:
            # Flat structure
            self.folder_structure = "flat"
            logger.info("Detected flat folder structure")
            
            for file_type in ["summary", "container", "variety"]:
                pattern = f"*_{file_type}_*.csv"
                files = list(self.base_dir.glob(pattern))
                validation[f"{file_type}_files"] = [f.name for f in files]
                logger.info(f"Found {len(files)} {file_type} files")
        
        return validation