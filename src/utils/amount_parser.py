"""
Amount parsing utilities for Fipro.

This module provides functions for parsing monetary amounts from various
formats, handling commas, currency symbols, and converting to Decimal
for precise financial calculations.
"""

from decimal import Decimal, InvalidOperation
import re
from decimal import Decimal, InvalidOperation


def parse_amount(amount_str: str) -> Decimal:
    """
    Parse amount string to Decimal.

    Handles:
    - Currency symbols (₹, Rs, Rs., etc.)
    - Thousand separators (commas)
    - Decimal points
    - Negative signs

    Args:
        amount_str: Amount string (e.g., "₹1,234.56", "Rs 5000.00")

    Returns:
        Decimal amount

    Raises:
        ValueError: If amount cannot be parsed

    Suggested implementation:
    - Remove currency symbols using regex
    - Remove commas
    - Strip whitespace
    - Convert to Decimal
    - Return Decimal object
    """
    cleaned = clean_amount_string(amount_str)
    if not cleaned:
        raise ValueError(f"Cannot parse empty amount string: {amount_str!r}")
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse amount string: {amount_str!r}") from exc


def clean_amount_string(amount_str: str) -> str:
    """
    Clean amount string by removing currency symbols and formatting.

    Args:
        amount_str: Raw amount string

    Returns:
        Cleaned numeric string
    """
    if amount_str is None:
        return ""

    s = str(amount_str).strip()

    # Detect and preserve negativity expressed via parentheses, e.g. (1,234.50)
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()

    # Remove common currency markers
    s = re.sub(r"(INR|Rs\.?|₹)", "", s, flags=re.IGNORECASE)

    # Remove all characters except digits, minus sign, and decimal point
    s = re.sub(r"[^0-9\.\-]", "", s)

    # Remove thousand separators (commas) while keeping decimal point
    # At this point commas should already be stripped by the regex above,
    # but keep this for safety if config changes.
    s = s.replace(",", "")

    s = s.strip()
    if not s:
        return ""

    # Ensure a single leading minus sign if negative
    if negative and not s.startswith("-"):
        s = "-" + s

    return s


def is_negative(amount_str: str) -> bool:
    """
    Check if amount string represents a negative value.

    Args:
        amount_str: Amount string

    Returns:
        True if negative, False otherwise
    """
    if amount_str is None:
        return False

    s = str(amount_str).strip()

    # Parentheses notation for negative values
    if s.startswith("(") and s.endswith(")"):
        return True

    cleaned = clean_amount_string(s)
    return cleaned.startswith("-")
