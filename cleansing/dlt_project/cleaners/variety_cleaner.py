from .base_cleaner import BaseCleaner
from ..utils.product_parser import ProductParser
from typing import Dict, Any, Optional
from decimal import Decimal
import logging
import json

logger = logging.getLogger(__name__)


class VarietyCleaner(BaseCleaner):
    """Cleaner for variety table data - STANDARDIZED column names"""
    
    def __init__(self, remove_non_analytics: bool = True):
        super().__init__(remove_non_analytics)
        logger.info("=" * 60)
        logger.info("VARIETY CLEANER INITIALIZED WITH DEBUG LOGGING")
        logger.info("=" * 60)


    def _clean_specific_row(self, row: Dict[str, Any], file_metadata: Dict) -> Optional[Dict[str, Any]]:
        """
        Clean a single variety row.
        Variety data has simple numbers (no MTD format), so we use _clean_decimal directly.
        """
        # Log the raw row for debugging
        logger.info(f"RAW VARIETY ROW: {row}")
        logger.info(f"Total Value Sold: {row.get('Total Value Sold')} (type: {type(row.get('Total Value Sold')).__name__})")
        logger.info(f"Total Qty Sold: {row.get('Total Qty Sold')} (type: {type(row.get('Total Qty Sold')).__name__})")
        logger.info(f"Total Kg Sold: {row.get('Total Kg Sold')} (type: {type(row.get('Total Kg Sold')).__name__})")
        
        # Extract commodity
        commodity_raw = (
            row.get("commodity") or 
            row.get("Commodity") or
            file_metadata.get("file_commodity")
        )
        
        if not commodity_raw:
            logger.debug("Skipping row with no commodity")
            return None
        
        # Get product combination
        product_combination = row.get("Product Combination", "")
        
        # Parse product combination
        parsed_product = ProductParser.parse(product_combination)
        
        # DIRECT DECIMAL PARSING - NO MTD HANDLING
        
        # Variety data has simple numbers, possibly with currency symbols
        today_value = self._clean_decimal(row.get("Total Value Sold", ""))
        today_qty = self._clean_decimal(row.get("Total Qty Sold", ""))
        today_kg = self._clean_decimal(row.get("Total Kg Sold", ""))
        
        # Price fields - also simple decimals
        avg_price = self._clean_decimal(row.get("Average", ""))
        highest_price = self._clean_decimal(row.get("Highest Price", ""))
        avg_per_kg = self._clean_decimal(row.get("Ave per Kg", ""))
        highest_per_kg = self._clean_decimal(row.get("Highest Price per Kg", ""))
        
        # Unit mass
        unit_mass = self._clean_decimal(row.get("Unit Mass", ""))
        
        # Clean and standardize date
        scrape_date = self._clean_date(row.get("scrape_date") or row.get("Date"))
        
        # Build cleaned row
        cleaned_row = {
            # Core identifiers
            "market": self._clean_text(file_metadata.get("market", "unknown")),
            "commodity": self._normalize_commodity(commodity_raw),
            "scrape_date": scrape_date,
            "file_date": self._clean_date(file_metadata.get("file_date")),
            
            # Container reference
            "container_name": self._clean_text(row.get("Container", "")),
            "unit_mass": unit_mass,
            
            # Parsed product details
            "variety": parsed_product.get("variety"),
            "product_class": parsed_product.get("product_class"),
            "product_size": parsed_product.get("product_size"),
            "product_count": parsed_product.get("product_count"),
            "product_color": parsed_product.get("product_color"),
            
            # STANDARDIZED column names - SIMPLE DECIMALS
            "value_sold": today_value,
            "qty_sold": today_qty,
            "kg_sold": today_kg,
            
            # Price metrics
            "average_price": avg_price,
            "highest_price": highest_price,
            "average_price_per_kg": avg_per_kg,
            "highest_price_per_kg": highest_per_kg,
            
            # Metadata
            "link_type": self._clean_text(row.get("link_type")),
            "source_filename": self._clean_text(file_metadata.get("filename")),
            "file_commodity": self._normalize_commodity(file_metadata.get("file_commodity")),
            "original_product_string": parsed_product.get("original_string"),
        }
        
        # Add ingestion_run_id if not removing non-analytics
        if not self.remove_non_analytics:
            cleaned_row["ingestion_run_id"] = self._clean_text(row.get("ingestion_run_id"))
        
        # Log the final cleaned row
        logger.info(f"CLEANED ROW - value_sold: {today_value}, qty_sold: {today_qty}, kg_sold: {today_kg}")
        
        return cleaned_row
    
    def _parse_combined_value_field(self, field: str) -> tuple:
        """
        Parse combined value field like "R2,800.00MTD: R46,400.00"
        Returns (today_value, mtd_value) as Decimal or None
        """
        logger.info(f"    Parsing combined value: '{field}'")
        
        if not field or field == "":
            logger.info("    Empty field, returning (None, None)")
            return None, None
        
        try:
            # Split on "MTD:" 
            if "MTD:" in field:
                parts = field.split("MTD:")
                today_part = parts[0].strip()
                mtd_part = parts[1].strip() if len(parts) > 1 else ""
                
                logger.info(f"    Split - today: '{today_part}', mtd: '{mtd_part}'")
                
                # Clean and parse today value
                today_value = self._clean_decimal(today_part)
                mtd_value = self._clean_decimal(mtd_part)
                
                logger.info(f"    Parsed - today: {today_value}, mtd: {mtd_value}")
                return today_value, mtd_value
            else:
                # No MTD, treat entire field as today value
                logger.info(f"    No MTD found, parsing whole field as today value")
                today_value = self._clean_decimal(field)
                logger.info(f"    Parsed today: {today_value}")
                return today_value, None
                
        except Exception as e:
            logger.error(f"    Error parsing combined value '{field}': {e}")
            return None, None
    
    def _parse_combined_quantity_field(self, field: str) -> tuple:
        """
        Parse combined quantity field like "7MTD: 115"
        Returns (today_qty, mtd_qty) as Decimal or None
        """
        logger.info(f"    Parsing combined quantity: '{field}'")
        
        if not field or field == "":
            logger.info("    Empty field, returning (None, None)")
            return None, None
        
        try:
            # Split on "MTD:"
            if "MTD:" in field:
                parts = field.split("MTD:")
                today_part = parts[0].strip()
                mtd_part = parts[1].strip() if len(parts) > 1 else ""
                
                logger.info(f"    Split - today: '{today_part}', mtd: '{mtd_part}'")
                
                # Clean and parse today quantity
                today_qty = self._clean_decimal(today_part)
                mtd_qty = self._clean_decimal(mtd_part)
                
                logger.info(f"    Parsed - today: {today_qty}, mtd: {mtd_qty}")
                return today_qty, mtd_qty
            else:
                # No MTD, treat entire field as today quantity
                logger.info(f"    No MTD found, parsing whole field as today quantity")
                today_qty = self._clean_decimal(field)
                logger.info(f"    Parsed today: {today_qty}")
                return today_qty, None
                
        except Exception as e:
            logger.error(f"    Error parsing combined quantity '{field}': {e}")
            return None, None