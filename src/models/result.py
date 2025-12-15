"""
Processing result models for Fipro.

This module defines data structures for tracking processing results and pipeline
outputs. Used by the orchestrator to report on file processing status.
"""

from dataclasses import dataclass
from typing import List
from src.models.transactions import Transaction


@dataclass
class ProcessingResult:
    """
    Result of processing a bank statement file.
    
    Attributes:
        source_file: Path to the source file
        bank: Bank name (HDFC, SBI, AXIS)
        total_transactions: Total transactions found
        successful: Successfully processed transactions
        failed: Failed to process transactions
        duplicates_skipped: Number of duplicate transactions skipped
        transactions: List of extracted Transaction objects
        errors: List of error messages
        warnings: List of warning messages
    """
    source_file: str
    bank: str
    total_transactions: int
    successful: int
    failed: int
    duplicates_skipped: int
    transactions: List[Transaction]
    errors: List[str]
    warnings: List[str]

