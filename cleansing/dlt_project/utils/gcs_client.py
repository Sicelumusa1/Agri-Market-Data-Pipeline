from google.cloud import storage
from typing import List, Iterator
import logging

logger = logging.getLogger(__name__)

class GCSClient:
    """Wrapper for GCS operations"""
    
    def __init__(self, bucket_name: str, credentials_path: str = None):
        if credentials_path:
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            self.client = storage.Client()
        
        self.bucket = self.client.bucket(bucket_name)
        logger.info(f"Initialized GCS client for bucket: {bucket_name}")
    
    def list_files(self, pattern: str = None) -> List[str]:
        """List files in bucket, optionally matching pattern"""
        blobs = self.bucket.list_blobs()
        
        if pattern:
            import fnmatch
            files = [blob.name for blob in blobs if fnmatch.fnmatch(blob.name, pattern)]
        else:
            files = [blob.name for blob in blobs]
        
        logger.info(f"Found {len(files)} files matching pattern: {pattern}")
        return files
    
    def read_csv_as_dicts(self, filepath: str) -> Iterator[dict]:
        """Read CSV file from GCS and yield rows as dictionaries"""
        blob = self.bucket.blob(filepath)
        
        # Download and read CSV
        content = blob.download_as_text()
        lines = content.splitlines()
        
        if not lines:
            return
        
        # Parse CSV
        headers = [h.strip() for h in lines[0].split(',')]
        
        for line in lines[1:]:
            if not line.strip():
                continue
                
            values = [v.strip() for v in line.split(',')]
            # Handle quoted values with commas
            if len(values) != len(headers):
                # Simple quote handling
                values = self._parse_csv_line(line)
            
            yield dict(zip(headers, values))
    
    def _parse_csv_line(self, line: str) -> List[str]:
        """Simple CSV line parser handling quotes"""
        import csv
        from io import StringIO
        
        reader = csv.reader(StringIO(line))
        return next(reader)