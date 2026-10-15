"""
Base parser interface for bank statement parsers.

This module defines the abstract base class that all bank-specific parsers must
implement. Provides a common interface for parsing different bank statement formats.
"""

from abc import ABC, abstractmethod

import pandas as pd

from src.models.transactions import Transaction


class BankParser(ABC):
    """
    Abstract base class for bank-specific parsers.

    Each bank (HDFC, SBI, Axis) implements this interface to handle their
    specific statement format, column names, and date formats.
    """

    @property
    @abstractmethod
    def bank_name(self) -> str:
        """
        Return bank identifier.

        Returns:
            Bank name (HDFC, SBI, AXIS)
        """
        pass

    @abstractmethod
    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        """
        Check if this parser can handle the file.

        Args:
            filename: Name of the file
            df: DataFrame loaded from the file

        Returns:
            True if this parser can handle the file, False otherwise
        """
        pass

    @abstractmethod
    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list[Transaction]:
        """
        Extract transactions from dataframe.

        Args:
            df: DataFrame with header row set correctly
            source_file: Path to source file for metadata

        Returns:
            List of Transaction objects
        """
        pass

    @staticmethod
    def cell_text(value: object) -> str:
        """Return a stripped string value while treating pandas nulls as empty."""
        if pd.isna(value):
            return ""
        return str(value).strip()
