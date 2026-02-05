import re
from decimal import Decimal
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class BaseCleaner(ABC):
    """Base class with shared cleaning operations"""
    
    # Fields to remove from final output (not useful for analytics)
    NON_ANALYTICS_FIELDS = ['link_type', 'ingestion_run_id']
    
    def clean_row(self, row: Dict[str, Any], file_metadata: Dict) -> Dict[str, Any]:
        """Main cleaning method - template pattern"""
        try:
            cleaned = self._clean_specific_row(row, file_metadata)
            return self._remove_non_analytics_fields(cleaned)
        except Exception as e:
            logger.error(f"Error cleaning row: {e}")
            # Return minimal valid row with error info
            return {
                "market": file_metadata.get("market", "unknown"),
                "commodity": row.get("commodity", "unknown"),
                "scrape_date": None,
                "file_date": file_metadata.get("file_date"),
                "cleaning_error": str(e),
                "source_filename": file_metadata.get("filename")
            }
    
    @abstractmethod
    def _clean_specific_row(self, row: Dict[str, Any], file_metadata: Dict) -> Dict[str, Any]:
        """Subclasses must implement this"""
        pass
    
    def _remove_non_analytics_fields(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Remove fields not needed for price/market analytics"""
        if not hasattr(self, 'remove_non_analytics') or self.remove_non_analytics:
            return {k: v for k, v in row.items() if k not in self.NON_ANALYTICS_FIELDS}
        return row
    
    # ========== SHARED CLEANING OPERATIONS ==========
    
    def _extract_primary_value(self, value_str: str) -> Decimal:
        """Extract primary value from 'R2,301,606.00MTD: R23,232,295.00'"""
        if not value_str or pd.isna(value_str):
            return Decimal('0.00')
        
        try:
            primary_part = str(value_str).split('MTD:')[0].strip()
            match = re.search(r'R?\s*([\d,]+\.?\d*)', primary_part)
            if match:
                numeric_str = match.group(1).replace(',', '')
                return Decimal(numeric_str)
        except Exception as e:
            logger.warning(f"Failed to extract primary value from '{value_str}': {e}")
        
        return Decimal('0.00')
    
    def _extract_mtd_value(self, value_str: str) -> Decimal:
        """Extract MTD value from value string"""
        if not value_str or 'MTD:' not in str(value_str):
            return Decimal('0.00')
        
        try:
            mtd_part = str(value_str).split('MTD:')[1].strip()
            match = re.search(r'R?\s*([\d,]+\.?\d*)', mtd_part)
            if match:
                numeric_str = match.group(1).replace(',', '')
                return Decimal(numeric_str)
        except Exception as e:
            logger.warning(f"Failed to extract MTD value from '{value_str}': {e}")
        
        return Decimal('0.00')
    
    def _extract_primary_quantity(self, qty_str: str) -> Decimal:
        """Extract primary quantity from '11,279MTD: 121,133'"""
        if not qty_str or pd.isna(qty_str):
            return Decimal('0.00')
        
        try:
            primary_part = str(qty_str).split('MTD:')[0].strip()
            match = re.search(r'([\d,]+)', primary_part)
            if match:
                numeric_str = match.group(1).replace(',', '')
                return Decimal(numeric_str)
        except Exception as e:
            logger.warning(f"Failed to extract primary quantity from '{qty_str}': {e}")
        
        return Decimal('0.00')
    
    def _extract_mtd_quantity(self, qty_str: str) -> Decimal:
        """Extract MTD quantity"""
        if not qty_str or 'MTD:' not in str(qty_str):
            return Decimal('0.00')
        
        try:
            mtd_part = str(qty_str).split('MTD:')[1].strip()
            match = re.search(r'([\d,]+)', mtd_part)
            if match:
                numeric_str = match.group(1).replace(',', '')
                return Decimal(numeric_str)
        except Exception as e:
            logger.warning(f"Failed to extract MTD quantity from '{qty_str}': {e}")
        
        return Decimal('0.00')
    
    def _clean_decimal(self, value: Any) -> Decimal:
        """Clean decimal values like '4722.00' or 'R18.76'"""
        if not value or pd.isna(value):
            return Decimal('0.00')
        
        try:
            # Remove currency symbol if present
            value_str = str(value).replace('R', '').strip()
            match = re.search(r'([\d,]+\.?\d*)', value_str)
            if match:
                numeric_str = match.group(1).replace(',', '')
                return Decimal(numeric_str)
        except Exception as e:
            logger.warning(f"Failed to clean decimal from '{value}': {e}")
        
        return Decimal('0.00')
    
    def _clean_date(self, date_str: Any) -> Optional[datetime.date]:
        """Clean date like '15 January 2026'"""
        if not date_str or pd.isna(date_str):
            return None
        
        try:
            # Try multiple date formats
            date_formats = ['%d %B %Y', '%d %b %Y', '%Y-%m-%d', '%d/%m/%Y']
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(str(date_str).strip(), fmt).date()
                except ValueError:
                    continue
                    
            logger.warning(f"Could not parse date: {date_str}")
        except Exception as e:
            logger.warning(f"Failed to clean date '{date_str}': {e}")
        
        return None
    
    def _normalize_commodity(self, commodity_str: Any) -> str:
        """Normalize commodity name"""
        if not commodity_str or pd.isna(commodity_str):
            return "unknown"
        
        try:
            return str(commodity_str).lower().strip()
        except:
            return "unknown"
    
    def _clean_text(self, text: Any) -> Optional[str]:
        """Clean text fields"""
        if not text or pd.isna(text):
            return None
        
        try:
            cleaned = str(text).strip()
            return cleaned if cleaned else None
        except:
            return None

# Import pandas for pd.isna checks
try:
    import pandas as pd
except ImportError:
    # Fallback for environments without pandas
    class DummyPd:
        @staticmethod
        def isna(value):
            return value is None or str(value).strip() == ''
    pd = DummyPd()