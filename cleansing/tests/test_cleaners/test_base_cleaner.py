"""
Unit tests for BaseCleaner.

These tests verify:
- The template method behavior of clean_row
- Proper error handling and fallback row creation
- Removal (and optional retention) of non-analytics fields
- Correct behavior of shared cleaning utility methods

BaseCleaner is an abstract class, so dummy subclasses are used
to test its concrete behavior.
"""

from decimal import Decimal
from datetime import date

import pytest

from dlt_project.cleaners.base_cleaner import BaseCleaner


class DummyCleaner(BaseCleaner):
    """
    Minimal concrete implementation of BaseCleaner
    for testing normal (successful) behavior.
    """

    def _clean_specific_row(self, row, file_metadata):
        """
        Return a predictable cleaned row including
        non-analytics fields for removal testing.
        """
        return {
            "market": file_metadata["market"],
            "commodity": row["commodity"],
            "price": row.get("price"),
            "link_type": "internal",
            "ingestion_run_id": "123",
        }


class FailingCleaner(BaseCleaner):
    """
    Cleaner that always raises an exception,
    used to test error handling in clean_row.
    """

    def _clean_specific_row(self, row, file_metadata):
        raise ValueError("boom")


# clean_row (template method) tests


def test_clean_row_removes_non_analytics_fields():
    """
    clean_row should remove fields listed in NON_ANALYTICS_FIELDS
    by default after successful cleaning.
    """
    cleaner = DummyCleaner()

    row = {"commodity": "Apples", "price": "R10.00"}
    file_metadata = {"market": "Joburg", "file_date": "2026-01-15"}

    result = cleaner.clean_row(row, file_metadata)

    assert result["market"] == "Joburg"
    assert result["commodity"] == "Apples"
    assert "link_type" not in result
    assert "ingestion_run_id" not in result


def test_clean_row_keeps_non_analytics_fields_when_disabled():
    """
    clean_row should retain non-analytics fields when
    remove_non_analytics is explicitly set to False.
    """
    cleaner = DummyCleaner()
    cleaner.remove_non_analytics = False

    row = {"commodity": "Apples", "price": "R10.00"}
    file_metadata = {"market": "Joburg"}

    result = cleaner.clean_row(row, file_metadata)

    assert "link_type" in result
    assert "ingestion_run_id" in result


def test_clean_row_handles_exception_and_returns_fallback():
    """
    clean_row should catch exceptions raised during cleaning
    and return a minimal, valid fallback row with error details.
    """
    cleaner = FailingCleaner()

    row = {"commodity": "Apples"}
    file_metadata = {
        "market": "Joburg",
        "file_date": "2026-01-15",
        "filename": "test.csv",
    }

    result = cleaner.clean_row(row, file_metadata)

    assert result["market"] == "Joburg"
    assert result["commodity"] == "Apples"
    assert result["cleaning_error"] == "boom"
    assert result["source_filename"] == "test.csv"



# Value extraction helpers


def test_extract_primary_value():
    """
    _extract_primary_value should extract the main value
    before the 'MTD:' marker.
    """
    cleaner = DummyCleaner()
    value = "R2,301,606.00MTD: R23,232,295.00"

    assert cleaner._extract_primary_value(value) == Decimal("2301606.00")


def test_extract_mtd_value():
    """
    _extract_mtd_value should extract the value after
    the 'MTD:' marker.
    """
    cleaner = DummyCleaner()
    value = "R2,301,606.00MTD: R23,232,295.00"

    assert cleaner._extract_mtd_value(value) == Decimal("23232295.00")



# Quantity extraction helpers


def test_extract_primary_quantity():
    """
    _extract_primary_quantity should extract the quantity
    before the 'MTD:' marker.
    """
    cleaner = DummyCleaner()
    qty = "11,279MTD: 121,133"

    assert cleaner._extract_primary_quantity(qty) == Decimal("11279")


def test_extract_mtd_quantity():
    """
    _extract_mtd_quantity should extract the quantity
    after the 'MTD:' marker.
    """
    cleaner = DummyCleaner()
    qty = "11,279MTD: 121,133"

    assert cleaner._extract_mtd_quantity(qty) == Decimal("121133")



# Decimal cleaning


def test_clean_decimal_currency_and_nulls():
    """
    _clean_decimal should:
    - Remove currency symbols
    - Handle null or empty values safely
    """
    cleaner = DummyCleaner()

    assert cleaner._clean_decimal("R18.76") == Decimal("18.76")
    assert cleaner._clean_decimal(None) == Decimal("0.00")
    assert cleaner._clean_decimal("") == Decimal("0.00")



# Date cleaning

def test_clean_date_multiple_formats():
    """
    _clean_date should successfully parse supported
    date formats and return a date object.
    """
    cleaner = DummyCleaner()

    assert cleaner._clean_date("15 January 2026") == date(2026, 1, 15)
    assert cleaner._clean_date("2026-01-15") == date(2026, 1, 15)
    assert cleaner._clean_date("15/01/2026") == date(2026, 1, 15)


def test_clean_date_invalid_returns_none():
    """
    _clean_date should return None for unparseable values.
    """
    cleaner = DummyCleaner()

    assert cleaner._clean_date("not-a-date") is None


# Text normalization helpers


def test_normalize_commodity():
    """
    _normalize_commodity should lowercase and trim
    commodity names, or return 'unknown' if missing.
    """
    cleaner = DummyCleaner()

    assert cleaner._normalize_commodity(" Apples ") == "apples"
    assert cleaner._normalize_commodity(None) == "unknown"


def test_clean_text():
    """
    _clean_text should trim whitespace and return None
    for empty or null values.
    """
    cleaner = DummyCleaner()

    assert cleaner._clean_text(" hello ") == "hello"
    assert cleaner._clean_text("") is None
    assert cleaner._clean_text(None) is None
