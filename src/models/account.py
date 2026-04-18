"""
Account and file metadata models for Fipro.

This module defines data structures for representing bank accounts and discovered
files during the ingestion phase.
"""

import os
from dataclasses import dataclass, field


@dataclass(slots=True)
class Account:
    """
    Represents a bank account.

    Attributes:
        bank: Bank name (HDFC, SBI, AXIS)
        account_number: Account number (last 4 digits only for security)
        nickname: Account nickname (e.g., "Salary Account", "Daily Expenses")
        account_type: Type of account (savings, current)
        is_active: Whether the account is currently active
    """

    bank: str
    account_number: str
    nickname: str
    account_type: str
    is_active: bool = True


@dataclass(slots=True)
class CrawledFile:
    """
    Metadata for a discovered file during ingestion.

    Attributes:
        filepath: Full path to the file
        extension: File extension (xls, xlsx, csv, pdf)
        size: File size in bytes
        crawl_date: ISO format timestamp when file was discovered
        metadata: Additional metadata dictionary for custom info
    """

    filepath: str
    extension: str
    size: int
    crawl_date: str
    metadata: dict = field(default_factory=dict)

    @property
    def filename(self) -> str:
        """Extract filename from filepath."""
        return self.filepath.split("/")[-1]

    @property
    def is_readable(self) -> bool:
        """Check if file is readable."""
        return os.access(self.filepath, os.R_OK)
