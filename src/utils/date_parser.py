"""
Date parsing utilities for Fipro.

This module provides functions for parsing bank-specific date formats and
converting them to standard Python date objects. Handles various date formats
used by different banks.
"""

from datetime import date, datetime


def parse_date(date_str: str, format_str: str) -> date:
    """
    Parse date string using specified format.

    Args:
        date_str: Date string to parse
        format_str: strftime format string (e.g., "%d/%m/%y", "%d-%m-%Y")

    Returns:
        date object

    Raises:
        ValueError: If date cannot be parsed with given format

    Suggested implementation:
    - Use datetime.strptime() with format_str
    - Return date() object
    """
    date_str = date_str.strip()
    parsed = datetime.strptime(date_str, format_str)
    return parsed.date()


def parse_date_multiple_formats(date_str: str, formats: list[str]) -> date | None:
    """
    Try parsing date with multiple format strings.

    Attempts each format in order until one succeeds.

    Args:
        date_str: Date string to parse
        formats: List of strftime format strings to try

    Returns:
        date object if successful, None otherwise

    Suggested implementation:
    - Iterate through formats list
    - Try parse_date() for each format
    - Return first successful parse
    - Return None if all formats fail
    """
    date_str = date_str.strip()
    for fmt in formats:
        try:
            return parse_date(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_hdfc_date(date_str: str) -> date:
    """
    Parse HDFC date format (DD/MM/YY or DD-MM-YYYY).

    Args:
        date_str: HDFC date string

    Returns:
        date object
    """
    parsed = parse_date_multiple_formats(date_str, ["%d/%m/%y", "%d-%m-%Y"])
    if parsed is None:
        raise ValueError(f"Unable to parse HDFC date: {date_str!r}")
    return parsed


def parse_sbi_date(date_str: str) -> date:
    """
    Parse SBI date format (DD MMM YYYY, e.g., "15 Nov 2025").

    Args:
        date_str: SBI date string

    Returns:
        date object
    """
    # Example format: "15 Nov 2025"
    return parse_date(date_str, "%d %b %Y")


def parse_axis_date(date_str: str) -> date:
    """
    Parse Axis date format (DD-MM-YYYY).

    Args:
        date_str: Axis date string

    Returns:
        date object
    """
    return parse_date(date_str, "%d-%m-%Y")
