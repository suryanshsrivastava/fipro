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
    def find_header_row(self, df: pd.DataFrame) -> int:
        """
        Find the row index where transaction data starts.

        Bank statements typically have preamble (logo, address, account details)
        before the actual transaction data begins.

        Args:
            df: DataFrame loaded from file

        Returns:
            Row index (0-based) where header row is located

        Raises:
            ValueError: If header row cannot be found
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

    @abstractmethod
    def get_column_mapping(self) -> dict:
        """
        Map bank-specific column names to standard schema.

        Returns:
            Dictionary mapping bank column names to standard names:
            {
                "transaction_date": ["Date", "Tran Date", ...],
                "description": ["Narration", "Description", ...],
                "debit": ["Withdrawal", "Debit", ...],
                "credit": ["Deposit", "Credit", ...],
                "balance": ["Balance", "Closing Balance", ...]
            }
        """
        pass

    @staticmethod
    def cell_text(value: object) -> str:
        """Return a stripped string value while treating pandas nulls as empty."""
        if pd.isna(value):
            return ""
        return str(value).strip()
