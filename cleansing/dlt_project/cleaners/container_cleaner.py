from .base_cleaner import BaseCleaner
from typing import Dict, Any, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class ContainerCleaner(BaseCleaner):
    """Cleaner for container table data - STANDARDIZED column names"""
    
    def __init__(self, remove_non_analytics: bool = True):
        super().__init__(remove_non_analytics)
    
    def _clean_specific_row(self, row: Dict[str, Any], file_metadata: Dict) -> Optional[Dict[str, Any]]:
        """
        Clean a single container row.
        STANDARDIZED column names (same as summary table).
        """
        # Normalize keys
        row_normalized = {k.lower(): v for k, v in row.items()}
        
        # Extract commodity
        commodity_raw = (
            row_normalized.get("commodity") or 
            row.get("Commodity") or
            file_metadata.get("file_commodity")
        )
        
        if not commodity_raw:
            logger.debug("Skipping row with no commodity")
            return None
        
        # Get field values
        value_field = row.get("Value Sold", "")
        qty_field = row.get("Qty Sold", "")
        kg_field = row.get("Kg Sold", "")
        qty_available_field = row.get("Qty Available", "")
        container_name_field = row.get("Container", "")
        avg_price_field = row.get("Average Price per Kg", "")
        
        # Parse combined fields using consolidated methods
        today_value, mtd_value = self._parse_combined_value_field(value_field)
        today_qty, mtd_qty = self._parse_combined_quantity_field(qty_field)
        today_kg, mtd_kg = self._parse_combined_quantity_field(kg_field)
        
        # Clean and standardize date
        scrape_date = self._clean_date(row.get("scrape_date") or row.get("Date"))
        
        # Build cleaned row with SAME column names as summary table
        cleaned_row = {
            # Core identifiers
            "market": self._clean_text(file_metadata.get("market", "unknown")),
            "commodity": self._normalize_commodity(commodity_raw),
            "scrape_date": scrape_date,  # date object -> YYYY-MM-DD in DB
            "file_date": self._clean_date(file_metadata.get("file_date")),
            
            # Container-specific fields
            "container_name": self._clean_text(container_name_field),
            
            # STANDARDIZED column names
            "value_sold": today_value,
            "value_sold_mtd": mtd_value,
            "qty_sold": today_qty,
            "qty_sold_mtd": mtd_qty,
            "kg_sold": today_kg,
            "kg_sold_mtd": mtd_kg,
            "qty_available": self._clean_decimal(qty_available_field),
            
            # Container-specific price
            "average_price_per_kg": self._clean_decimal(avg_price_field),
            
            # Metadata
            "link_type": self._clean_text(row_normalized.get("link_type")),
            "source_filename": self._clean_text(file_metadata.get("filename")),
            "file_commodity": self._normalize_commodity(file_metadata.get("file_commodity")),
        }
        
        # Add ingestion_run_id if not removing non-analytics
        if not self.remove_non_analytics:
            cleaned_row["ingestion_run_id"] = self._clean_text(row_normalized.get("ingestion_run_id"))
        
        return cleaned_row