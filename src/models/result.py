"""
Processing result models for Fipro.

This module defines data structures for tracking processing results and pipeline
outputs. Used by the orchestrator to report on file processing status.
"""

from dataclasses import dataclass

from src.models.transactions import Transaction


@dataclass(slots=True)
class HubSummary:
    """Compact snapshot for CLI and PipelineRun."""

    earliest: str | None
    latest: str | None
    cash_flow: dict | None
    total_across_statements: str | None
    reason_if_no_total: str | None

    @classmethod
    def empty(cls, reason: str = "no_input_files") -> HubSummary:
        return cls(
            earliest=None,
            latest=None,
            cash_flow=None,
            total_across_statements=None,
            reason_if_no_total=reason,
        )

    @classmethod
    def from_report(cls, report: dict) -> HubSummary:
        date_range = report.get("date_range") or {}
        ending = report.get("net_worth_proxy") or {}
        return cls(
            earliest=date_range.get("earliest"),
            latest=date_range.get("latest"),
            cash_flow=report.get("cash_flow"),
            total_across_statements=ending.get("total_across_statements"),
            reason_if_no_total=ending.get("reason_if_no_total"),
        )

    def __getitem__(self, key: str):
        mapping = {
            "date_range": {"earliest": self.earliest, "latest": self.latest},
            "cash_flow": self.cash_flow,
            "net_worth_proxy": {
                "total_across_statements": self.total_across_statements,
                "reason_if_no_total": self.reason_if_no_total,
            },
        }
        if key not in mapping:
            raise KeyError(key)
        return mapping[key]


@dataclass(slots=True)
class PipelineRun:
    """Outputs and transactions from a full pipeline run."""

    results: list[ProcessingResult]
    deduplicated_transactions: list[Transaction]
    goodbudget_csv_path: str
    report_json_path: str
    hub_csv_path: str
    dashboard_csv_path: str
    hub_summary: HubSummary


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
