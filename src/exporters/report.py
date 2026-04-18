"""Processing report generator for Fipro."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.models.result import ProcessingResult
from src.models.transactions import Transaction, TransactionStatus, TransactionType
from src.utils.report_helpers import (
    cash_flow_from_transactions,
    ending_balances_by_statement,
    filter_transactions_for_export,
    top_descriptions,
)


def generate_report(
    results: list[ProcessingResult],
    output_path: str,
    exported_transactions: int | None = None,
    config: dict | None = None,
    duplicates_skipped: int = 0,
) -> dict:
    """Generate and write a JSON processing report."""
    transactions = [transaction for result in results for transaction in result.transactions]
    include_internal_transfers = True
    if config is not None:
        processing = config.get("processing", {})
        if "include_internal_transfers" in processing:
            include_internal_transfers = processing["include_internal_transfers"]
        elif processing.get("skip_internal_transfers", False):
            include_internal_transfers = False
    transactions_for_metrics = filter_transactions_for_export(transactions, include_internal_transfers)

    by_bank: dict[str, dict[str, int]] = {}
    for transaction in transactions:
        bank_bucket = by_bank.setdefault(
            transaction.source_bank,
            {"transactions": 0, "debits": 0, "credits": 0},
        )
        bank_bucket["transactions"] += 1
        if transaction.transaction_type == TransactionType.DEBIT:
            bank_bucket["debits"] += 1
        else:
            bank_bucket["credits"] += 1

    date_range = calculate_date_range(transactions)
    ending_balances = ending_balances_by_statement(transactions)

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "summary": {
            "total_files": len(results),
            "total_transactions": sum(result.total_transactions for result in results),
            "exported_transactions": (
                len(transactions) if exported_transactions is None else exported_transactions
            ),
            "duplicates_skipped": duplicates_skipped,
            "transfers_detected": sum(
                1 for transaction in transactions if transaction.status == TransactionStatus.TRANSFER
            ),
            "failed_files": sum(1 for result in results if result.errors),
        },
        "by_bank": by_bank,
        "date_range": date_range,
        "cash_flow": cash_flow_from_transactions(transactions_for_metrics),
        "net_worth_proxy": ending_balances,
        "top_descriptions": top_descriptions(transactions_for_metrics),
        "files": sorted(
            [
                {
                    "source_file": Path(result.source_file).name,
                    "bank": result.bank,
                    "total_transactions": result.total_transactions,
                    "successful": result.successful,
                    "failed": result.failed,
                    "duplicates_skipped": result.duplicates_skipped,
                    "errors": result.errors,
                    "warnings": result.warnings,
                }
                for result in results
            ],
            key=lambda item: item["source_file"],
        ),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


def calculate_date_range(transactions: list[Transaction]) -> dict:
    """Calculate earliest and latest transaction dates."""
    if not transactions:
        return {"earliest": None, "latest": None}

    dates = sorted(transaction.transaction_date for transaction in transactions)
    return {
        "earliest": dates[0].isoformat(),
        "latest": dates[-1].isoformat(),
    }


def build_hub_summary(report: dict) -> dict:
    """Compact snapshot for CLI (subset of report)."""
    ending = report.get("net_worth_proxy") or {}
    return {
        "date_range": report.get("date_range"),
        "cash_flow": report.get("cash_flow"),
        "net_worth_proxy": {
            "total_across_statements": ending.get("total_across_statements"),
            "reason_if_no_total": ending.get("reason_if_no_total"),
        },
    }
