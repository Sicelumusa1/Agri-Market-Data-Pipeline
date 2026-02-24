import re
from decimal import Decimal
from datetime import datetime, date
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Handle pandas dependency gracefully
try:
    import pandas as pd
    _has_pandas = True
except ImportError:
    _has_pandas = False
    class DummyPd:
        @staticmethod
        def isna(value):
            return value is None or (isinstance(value, str) and value.strip() == '')
    pd = DummyPd()


class BaseCleaner(ABC):
    """Base class with shared cleaning operations - STANDARDIZED"""
    
    # Fields to remove from final output (not useful for analytics)
    NON_ANALYTICS_FIELDS = {'link_type', 'ingestion_run_id', 'source_filename', 
                           'file_commodity', 'file_date', 'scrape_id', 'run_id', 
                           'timestamp', 'extraction_time'}
    
    def __init__(self, remove_non_analytics: bool = True):
        self.remove_non_analytics = remove_non_analytics
    
    def clean_row(self, row: Dict[str, Any], file_metadata: Dict) -> Optional[Dict[str, Any]]:
        """Main cleaning method - template pattern"""
        try:
            cleaned = self._clean_specific_row(row, file_metadata)
            if cleaned:
                cleaned = self._remove_non_analytics_fields(cleaned)
            return cleaned
        except Exception as e:
            logger.error(f"Error cleaning row: {e}")
            # Return minimal valid row with error info for debugging
            return {
                "market": file_metadata.get("market", "unknown"),
                "commodity": self._normalize_commodity(row.get("commodity", row.get("Commodity", "unknown"))),
                "scrape_date": self._clean_date(row.get("scrape_date") or row.get("Date")),
                "file_date": self._clean_date(file_metadata.get("file_date")),
                "cleaning_error": str(e),
                "source_filename": file_metadata.get("filename")
            }
    
    @abstractmethod
    def _clean_specific_row(self, row: Dict[str, Any], file_metadata: Dict) -> Optional[Dict[str, Any]]:
        """Subclasses must implement this"""
        pass
    
    def _remove_non_analytics_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Remove fields not needed for price/market analytics"""
        if self.remove_non_analytics:
            return {k: v for k, v in row.items() if k not in self.NON_ANALYTICS_FIELDS}
        return row
    
    # SHARED PARSING METHODS
    
    def _parse_combined_value_field(self, value_str: Any) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Parse a value field that contains both today's value and MTD value.
        Returns (today_value, mtd_value) as Decimals, or (None, None) if unparseable.
        
        Examples:
            "R310.00MTD: R2,200.00" -> (Decimal('310.00'), Decimal('2200.00'))
            "R0.00MTD: R0.00" -> (Decimal('0.00'), Decimal('0.00'))
            "R53,770.00MTD: R8,808,099.00" -> (Decimal('53770.00'), Decimal('8808099.00'))
        """
        if not value_str or pd.isna(value_str):
            return None, None
        
        value_str = str(value_str).strip()
        
        try:
            # Today's value (before MTD:)
            today_value = None
            if 'MTD:' in value_str:
                today_part = value_str.split('MTD:')[0].strip()
            else:
                today_part = value_str
            
            today_match = re.search(r'R?\s*([\d,]+\.?\d*)', today_part)
            if today_match:
                today_value = self._parse_decimal(today_match.group(1))
            
            # MTD value (after MTD:)
            mtd_value = None
            if 'MTD:' in value_str:
                mtd_part = value_str.split('MTD:')[1].strip()
                mtd_match = re.search(r'R?\s*([\d,]+\.?\d*)', mtd_part)
                if mtd_match:
                    mtd_value = self._parse_decimal(mtd_match.group(1))
            
            return today_value, mtd_value
            
        except Exception as e:
            logger.debug(f"Failed to parse value field '{value_str}': {e}")
            return None, None
    
    def _parse_combined_quantity_field(self, qty_str: Any) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """
        Parse a quantity field that contains both today's quantity and MTD quantity.
        Returns (today_qty, mtd_qty) as Decimals, or (None, None) if unparseable.
        
        Examples:
            "6MTD: 54" -> (Decimal('6'), Decimal('54'))
            "1,131MTD: 2,200" -> (Decimal('1131'), Decimal('2200'))
            "32,921MTD: 528,665" -> (Decimal('32921'), Decimal('528665'))
        """
        if not qty_str or pd.isna(qty_str):
            return None, None
        
        qty_str = str(qty_str).strip()
        
        try:
            # Today's quantity (before MTD:)
            today_qty = None
            if 'MTD:' in qty_str:
                today_part = qty_str.split('MTD:')[0].strip()
            else:
                today_part = qty_str
            
            today_match = re.search(r'([\d,]+)', today_part)
            if today_match:
                today_qty = self._parse_decimal(today_match.group(1))
            
            # MTD quantity (after MTD:)
            mtd_qty = None
            if 'MTD:' in qty_str:
                mtd_part = qty_str.split('MTD:')[1].strip()
                mtd_match = re.search(r'([\d,]+)', mtd_part)
                if mtd_match:
                    mtd_qty = self._parse_decimal(mtd_match.group(1))
            
            return today_qty, mtd_qty
            
        except Exception as e:
            logger.debug(f"Failed to parse quantity field '{qty_str}': {e}")
            return None, None
    
    def _parse_decimal(self, value_str: str) -> Optional[Decimal]:
        """Parse any decimal number string to Decimal, removing commas and currency symbols.
        Rounds to 2 decimal places for currency consistency."""
        if not value_str:
            return None
        try:
            # Remove commas, 'R', spaces and convert to Decimal
            cleaned = re.sub(r'[R,\s]', '', str(value_str))
            if cleaned:
                # Convert to Decimal and quantize to 2 decimal places
                value = Decimal(cleaned)
                # Round to 2 decimal places using ROUND_HALF_EVEN
                return value.quantize(Decimal('0.00'))
        except (ValueError, TypeError, Decimal.InvalidOperation):
            logger.debug(f"Failed to parse decimal: '{value_str}'")
        return None

    def _clean_decimal(self, value: Any) -> Optional[Decimal]:
        """
        Clean decimal values - returns 0.00 for zeros, None only for truly missing data.
        Rounds to 2 decimal places for consistency.
        """
        # Handle None, NaN, or empty string
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        
        if isinstance(value, str) and value.strip() == '':
            return None
        
        # If it's already a number, just quantize it
        if isinstance(value, (int, float, Decimal)):
            return Decimal(str(value)).quantize(Decimal('0.00'))
        
        # Handle string values
        if isinstance(value, str):
            value = value.strip()
            
            # Remove currency symbols, commas, and spaces
            cleaned = re.sub(r'[R,\s]', '', value)
            
            # If after cleaning it's empty, return None (truly missing)
            if not cleaned:
                return None
            
            try:
                # This will handle "0", "0.00", "R0.00" correctly - returning Decimal('0.00')
                return Decimal(cleaned).quantize(Decimal('0.00'))
            except (ValueError, TypeError, Decimal.InvalidOperation):
                logger.debug(f"Failed to clean decimal from '{value}'")
                return None
        
        # If it's something else, try to convert
        try:
            return Decimal(str(value)).quantize(Decimal('0.00'))
        except:
            return None
    
    def _clean_date(self, date_val: Any) -> Optional[date]:
        """
        Standardize dates to date objects (will be converted to YYYY-MM-DD in dlt).
        Handles '30 December 2025', '2026-01-15', '15/01/2026', etc.
        """
        if not date_val or pd.isna(date_val):
            return None
        
        date_str = str(date_val).strip()
        if not date_str:
            return None
        
        # If it's already a date object
        if isinstance(date_val, (datetime, date)):
            if isinstance(date_val, datetime):
                return date_val.date()
            return date_val
        
        # Try multiple date formats
        date_formats = [
            '%d %B %Y',     # 30 December 2025
            '%d %b %Y',     # 30 Dec 2025
            '%Y-%m-%d',     # 2026-01-15
            '%d/%m/%Y',     # 15/01/2026
            '%m/%d/%Y',     # 01/15/2026
            '%d-%m-%Y',     # 15-01-2026
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _normalize_commodity(self, commodity_str: Any) -> Optional[str]:
        """
        Normalize commodity name to UPPERCASE_WITH_UNDERSCORES.
        Example: 'English Cucumber' -> 'ENGLISH_CUCUMBER'
        """
        if not commodity_str or pd.isna(commodity_str):
            return None
        
        try:
            # Convert to uppercase, replace spaces with underscores, remove special chars
            cleaned = str(commodity_str).strip().upper()
            # Replace multiple spaces with single underscore
            cleaned = re.sub(r'\s+', '_', cleaned)
            # Remove any non-alphanumeric except underscore
            cleaned = re.sub(r'[^\w_]', '', cleaned)
            return cleaned if cleaned else None
        except:
            return None
    
    def _clean_text(self, text: Any) -> Optional[str]:
        """Clean text fields - returns None for empty strings"""
        if text is None or pd.isna(text):
            return None
        
        try:
            cleaned = str(text).strip()
            return cleaned if cleaned else None
        except:
            return None
    
    # LEGACY METHODS
    
    def _extract_primary_value(self, value_str: str) -> Decimal:
        """Legacy method - maintained for compatibility"""
        today, _ = self._parse_combined_value_field(value_str)
        return today or Decimal('0.00')
    
    def _extract_mtd_value(self, value_str: str) -> Decimal:
        """Legacy method - maintained for compatibility"""
        _, mtd = self._parse_combined_value_field(value_str)
        return mtd or Decimal('0.00')
    
    def _extract_primary_quantity(self, qty_str: str) -> Decimal:
        """Legacy method - maintained for compatibility"""
        today, _ = self._parse_combined_quantity_field(qty_str)
        return today or Decimal('0.00')
    
    def _extract_mtd_quantity(self, qty_str: str) -> Decimal:
        """Legacy method - maintained for compatibility"""
        _, mtd = self._parse_combined_quantity_field(qty_str)
        return mtd or Decimal('0.00')