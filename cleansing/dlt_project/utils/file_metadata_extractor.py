import re
from datetime import datetime
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class FileMetadataExtractor:
    """
    Extract metadata from filenames with multiple patterns.
    
    Handles both patterns:
    1. Simple: joburg_market_watermelons_summary_15 January 2026.csv
    2. Complex: joburg_market_amadumbe_container_9_February_2026_2026-02-10.csv
       - '9_February_2026' = scrape_date (from filename)
       - '2026-02-10' = process_run_date (when the file was generated)
    
    Commodity can have underscores: 'green_beans', 'baby_marrow', etc.
    Market can have underscores: 'eastern_cape_market', 'cape_town_market', etc.
    """
    
    # Pattern 1: Complex format with underscores in date and process date
    # Matches: market_commodity_type_dd_Month_yyyy_yyyy-mm-dd.csv
    # Market can have underscores: [a-z_]+? ensures non-greedy match
    COMPLEX_PATTERN = r'^(?P<market>[a-z_]+?)_market_(?P<commodity>[a-z_]+)_(?P<data_type>summary|container|variety)_(?P<scrape_date>\d{1,2}_[a-z]+_\d{4})_(?P<process_date>\d{4}-\d{2}-\d{2})\.csv$'
    
    # Pattern 2: Simple format with spaces in date
    # Matches: market_commodity_type_dd Month yyyy.csv
    SIMPLE_PATTERN = r'^(?P<market>[a-z_]+?)_market_(?P<commodity>[a-z_]+)_(?P<data_type>summary|container|variety)_(?P<date>\d{1,2} [a-z]+ \d{4})\.csv$'
    
    # Pattern 3: Alternative with only underscore date
    # Matches: market_commodity_type_dd_Month_yyyy.csv
    ALT_PATTERN = r'^(?P<market>[a-z_]+?)_market_(?P<commodity>[a-z_]+)_(?P<data_type>summary|container|variety)_(?P<date>\d{1,2}_[a-z]+_\d{4})\.csv$'
    
    # Fallback pattern for files without proper date formats
    # Looks for market ending with '_market' or just takes first part
    FALLBACK_PATTERN = r'^(?P<market>[a-z_]+(?:_market)?)_(?P<commodity>[a-z_]+)_(?P<data_type>summary|container|variety)_.*\.csv$'
    
    @staticmethod
    def extract(filename: str) -> Dict:
        """
        Extract metadata from filename, trying multiple patterns.
        
        Returns dict with:
        - market: e.g., 'joburg_market', 'eastern_cape_market'
        - commodity: e.g., 'amadumbe' (from filename)
        - data_type: 'summary', 'container', or 'variety'
        - scrape_date: Date from filename (primary date)
        - file_date: Alias for scrape_date (for backward compatibility)
        - process_run_date: Date when file was generated (if present)
        - filename: Original filename
        - full_path: Full file path
        """
        # Get just the filename from path
        basename = filename.split('/')[-1]
        
        # Try complex pattern first (has both dates)
        complex_match = re.match(FileMetadataExtractor.COMPLEX_PATTERN, basename.lower())
        if complex_match:
            logger.debug(f"Matched complex pattern: {basename}")
            market = complex_match.group('market') + '_market'
            return FileMetadataExtractor._parse_complex_match(complex_match, market, basename, filename)
        
        # Try simple pattern (space-separated date)
        simple_match = re.match(FileMetadataExtractor.SIMPLE_PATTERN, basename.lower())
        if simple_match:
            logger.debug(f"Matched simple pattern: {basename}")
            market = simple_match.group('market') + '_market'
            return FileMetadataExtractor._parse_simple_match(simple_match, market, basename, filename)
        
        # Try alternative pattern (underscore date, no process date)
        alt_match = re.match(FileMetadataExtractor.ALT_PATTERN, basename.lower())
        if alt_match:
            logger.debug(f"Matched alternative pattern: {basename}")
            market = alt_match.group('market') + '_market'
            return FileMetadataExtractor._parse_alt_match(alt_match, market, basename, filename)
        
        # Try fallback pattern
        fallback_match = re.match(FileMetadataExtractor.FALLBACK_PATTERN, basename.lower())
        if fallback_match:
            logger.debug(f"Matched fallback pattern: {basename}")
            return FileMetadataExtractor._parse_fallback_match(fallback_match, basename, filename)
        
        # No pattern matched
        logger.warning(f"Filename doesn't match any expected pattern: {basename}")
        return FileMetadataExtractor._create_fallback_metadata(basename, filename)
    
    @staticmethod
    def _parse_complex_match(match: re.Match, market: str, basename: str, full_path: str) -> Dict:
        """Parse complex pattern with both scrape_date and process_date"""
        scrape_date_str = match.group('scrape_date').replace('_', ' ')  
        process_date_str = match.group('process_date')  
        
        try:
            scrape_date = datetime.strptime(scrape_date_str, '%d %B %Y').date()
        except ValueError as e:
            logger.error(f"Failed to parse scrape date '{scrape_date_str}' from {basename}: {e}")
            scrape_date = None
        
        try:
            process_run_date = datetime.strptime(process_date_str, '%Y-%m-%d').date()
        except ValueError as e:
            logger.error(f"Failed to parse process date '{process_date_str}' from {basename}: {e}")
            process_run_date = None
        
        return {
            "market": market,  
            "file_commodity": match.group('commodity'),
            "data_type": match.group('data_type'),
            "scrape_date": scrape_date,      
            "file_date": scrape_date,        
            "process_run_date": process_run_date,  
            "filename": basename,
            "full_path": full_path,
            "pattern_used": "complex"
        }
    
    @staticmethod
    def _parse_simple_match(match: re.Match, market: str, basename: str, full_path: str) -> Dict:
        """Parse simple pattern with space-separated date"""
        date_str = match.group('date')  
        
        try:
            file_date = datetime.strptime(date_str, '%d %B %Y').date()
        except ValueError as e:
            logger.error(f"Failed to parse date '{date_str}' from {basename}: {e}")
            file_date = None
        
        return {
            "market": market,  
            "file_commodity": match.group('commodity'),
            "data_type": match.group('data_type'),
            "scrape_date": file_date,
            "file_date": file_date,
            "process_run_date": None,  
            "filename": basename,
            "full_path": full_path,
            "pattern_used": "simple"
        }
    
    @staticmethod
    def _parse_alt_match(match: re.Match, market: str, basename: str, full_path: str) -> Dict:
        """Parse alternative pattern with underscore date only"""
        date_str = match.group('date').replace('_', ' ')
        
        try:
            file_date = datetime.strptime(date_str, '%d %B %Y').date()
        except ValueError as e:
            logger.error(f"Failed to parse date '{date_str}' from {basename}: {e}")
            file_date = None
        
        return {
            "market": market,
            "file_commodity": match.group('commodity'),
            "data_type": match.group('data_type'),
            "scrape_date": file_date,
            "file_date": file_date,
            "process_run_date": None,
            "filename": basename,
            "full_path": full_path,
            "pattern_used": "alternative"
        }
    
    @staticmethod
    def _parse_fallback_match(match: re.Match, basename: str, full_path: str) -> Dict:
        """Parse fallback pattern (no date extraction)"""
        market = match.group('market')
        # If market doesn't end with '_market', add it for consistency
        if not market.endswith('_market'):
            market = market + '_market'
        
        return {
            "market": market,
            "file_commodity": match.group('commodity'),
            "data_type": match.group('data_type'),
            "scrape_date": None,
            "file_date": None,
            "process_run_date": None,
            "filename": basename,
            "full_path": full_path,
            "pattern_used": "fallback"
        }
    
    @staticmethod
    def _create_fallback_metadata(basename: str, full_path: str) -> Dict:
        """Create metadata when no pattern matches"""
        # Try to extract what we can with heuristics
        market = FileMetadataExtractor.extract_market(basename)
        data_type = FileMetadataExtractor.extract_data_type(basename)
        commodity = FileMetadataExtractor.extract_commodity(basename)
        
        return {
            "market": market,
            "file_commodity": commodity,
            "data_type": data_type,
            "scrape_date": None,
            "file_date": None,
            "process_run_date": None,
            "filename": basename,
            "full_path": full_path,
            "pattern_used": "error_fallback"
        }
    
    @staticmethod
    def extract_market(filename: str) -> str:
        """
        Extract market name from filename.
        Market is the part before the commodity, often ends with '_market'
        """
        basename = filename.split('/')[-1].lower()
        
        # Look for 'market' in the filename
        if '_market_' in basename:
            # Get everything up to and including 'market'
            parts = basename.split('_market_', 1)
            return parts[0] + '_market'
        
        # If no 'market' found, return first part as fallback
        parts = basename.split('_')
        return parts[0] if parts else "unknown"
    
    @staticmethod
    def extract_data_type(filename: str) -> str:
        """Extract data type from filename"""
        basename = filename.lower()
        
        # More precise matching
        if '_summary_' in basename or basename.endswith('_summary.csv'):
            return 'summary'
        elif '_container_' in basename or basename.endswith('_container.csv'):
            return 'container'
        elif '_variety_' in basename or basename.endswith('_variety.csv'):
            return 'variety'
        
        return 'unknown'
    
    @staticmethod
    def extract_commodity(filename: str) -> str:
        """Extract commodity name from filename (heuristic)"""
        basename = filename.split('/')[-1].lower().replace('.csv', '')
        
        # Find market
        market = FileMetadataExtractor.extract_market(filename)
        if market == "unknown":
            return "unknown"
        
        # Remove market from beginning
        rest = basename[len(market):].lstrip('_')
        
        # Find data_type
        data_type = FileMetadataExtractor.extract_data_type(filename)
        if data_type == "unknown":
            return "unknown"
        
        # Remove data_type from end (and everything after it)
        data_type_with_underscore = f"_{data_type}"
        if data_type_with_underscore in rest:
            commodity_part = rest.split(data_type_with_underscore, 1)[0]
            return commodity_part.rstrip('_')
        
        return "unknown"
    
    @staticmethod
    def validate_filename(filename: str) -> Tuple[bool, str]:
        """
        Validate if filename matches expected patterns.
        Returns (is_valid, error_message)
        """
        basename = filename.split('/')[-1]
        
        patterns_to_check = [
            (FileMetadataExtractor.COMPLEX_PATTERN, "complex"),
            (FileMetadataExtractor.SIMPLE_PATTERN, "simple"),
            (FileMetadataExtractor.ALT_PATTERN, "alternative"),
        ]
        
        for pattern, pattern_name in patterns_to_check:
            if re.match(pattern, basename.lower()):
                return True, f"Matches {pattern_name} pattern"
        
        # Check for common issues
        if not basename.endswith('.csv'):
            return False, "Filename must end with .csv"
        
        if not ('_summary' in basename or '_container' in basename or '_variety' in basename):
            return False, "Filename must contain _summary, _container, or _variety"
        
        return False, "Filename doesn't match any expected pattern"