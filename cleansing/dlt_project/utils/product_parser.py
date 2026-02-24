import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ProductParser:
    """
    Parse Product Combination field while preserving original size format.
    
    Notes:
        - '*' represents a wildcard meaning "all / unspecified / any"
        - Wildcard values are normalized to 'ANY' (string) for primary key compatibility
        - Positional meaning is assumed:
            [0]=variety, [1]=class, [2]=size, [3]=count, [4]=color
    
    Examples:
        - 'CRIPPS RED,CL 1,165,8,RED'    - size: '165'
        - 'CRIPPS RED,CL 2,L,*,*'        - size: 'L'
        - 'STARKING,CL 1,*,80,*'         - size: 'ANY'
    """
    
    @staticmethod
    def parse(product_str: str) -> Dict[str, Any]:
        """Parse product combination string - STANDARDIZED"""
        if not product_str or not isinstance(product_str, str):
            return ProductParser._empty_result(product_str)
        
        # Split by comma
        parts = ProductParser._safe_split(product_str)
        
        return {
            "variety": ProductParser._parse_variety(parts[0] if len(parts) > 0 else ""),
            "product_class": ProductParser._parse_class(parts[1] if len(parts) > 1 else ""),
            "product_size": ProductParser._parse_size(parts[2] if len(parts) > 2 else ""),
            "product_count": ProductParser._parse_count(parts[3] if len(parts) > 3 else ""),
            "product_color": ProductParser._parse_color(parts[4] if len(parts) > 4 else ""),
            "original_string": product_str
        }
    
    @staticmethod
    def _safe_split(product_str: str) -> list:
        """Safely split by comma"""
        return [part.strip() for part in product_str.split(',')]
    
    @staticmethod
    def _empty_result(product_str: Any) -> Dict[str, Any]:
        return {
            "variety": None,
            "product_class": None,
            "product_size": None,
            "product_count": None,
            "product_color": None,
            "original_string": str(product_str) if product_str else None
        }
    
    @staticmethod
    def _parse_variety(variety_str: str) -> Optional[str]:
        """
        Parse variety - normalize to UPPERCASE, wildcard becomes 'ANY'.
        This ensures primary key never has NULL values.
        """
        if not variety_str or variety_str == '*':
            return "ANY"  
        cleaned = variety_str.strip().upper()
        cleaned = re.sub(r'\s+', '_', cleaned)
        return cleaned if cleaned else "ANY"
    
    @staticmethod
    def _parse_class(class_str: str) -> Optional[str]:
        """
        Parse class: 'CL 1' → '1', 'LOWEST CLASS' → 'LOWEST', wildcard → 'ANY'
        """
        if not class_str or class_str == '*':
            return "ANY"
        
        class_lower = class_str.lower().strip()
        
        # Handle special cases
        if 'lowest' in class_lower:
            return 'LOWEST'
        
        # Extract numeric class
        match = re.search(r'cl\s*(\d+|one|two|three|four|five)', class_lower)
        if match:
            num_str = match.group(1)
            # Convert words to numbers
            word_to_num = {
                'one': '1', 'two': '2', 'three': '3',
                'four': '4', 'five': '5'
            }
            return word_to_num.get(num_str, num_str)
        
        # Normalize: uppercase
        return class_lower.upper()
    
    @staticmethod
    def _parse_size(size_str: str) -> Optional[str]:
        """
        Parse size - keep as string, wildcard becomes 'ANY'.
        Examples: '165', 'L', 'M', '2XL', etc.
        """
        if not size_str or size_str == '*':
            return "ANY"
        return size_str.strip().upper()
    
    @staticmethod
    def _parse_count(count_str: str) -> Optional[str]:
        """
        Parse count number - return as string to preserve leading zeros? No, counts don't have leading zeros.
        Wildcard becomes 'ANY'.
        """
        if not count_str or count_str == '*':
            return "ANY"
        
        try:
            # Convert to int then back to string to normalize (remove commas)
            cleaned = count_str.replace(',', '')
            return str(int(cleaned))
        except (ValueError, TypeError):
            logger.warning(f"Could not parse count from: {count_str}")
            return "ANY"  
    
    @staticmethod
    def _parse_color(color_str: str) -> Optional[str]:
        """
        Parse color - normalize to UPPERCASE, wildcard becomes 'ANY'.
        """
        if not color_str or color_str == '*':
            return "ANY"
        return color_str.strip().upper()