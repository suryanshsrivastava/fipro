"""
Processing result models for Fipro.

This module defines data structures for tracking processing results and pipeline
outputs. Used by the orchestrator to report on file processing status.
"""

from dataclasses import dataclass

from src.models.transactions import Transaction


@dataclass(slots=True)
class PipelineRun:
    """Outputs and transactions from a full pipeline run."""

    results: list["ProcessingResult"]
    deduplicated_transactions: list[Transaction]
    goodbudget_csv_path: str
    report_json_path: str
    hub_csv_path: str
    hub_summary: dict


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
    transactions: list[Transaction]
    errors: list[str]
    warnings: list[str]
