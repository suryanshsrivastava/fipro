"""Processing report generator for Fipro."""

from typing import List
from datetime import datetime, timezone
import json
from pathlib import Path

from src.models.result import ProcessingResult
from src.models.transactions import Transaction, TransactionType, TransactionStatus


def generate_report(
    results: List[ProcessingResult],
    output_path: str,
    exported_transactions: int | None = None,
) -> dict:
    """Generate and write a JSON processing report."""
    transactions = [
        transaction for result in results for transaction in result.transactions
    ]
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

    report = {
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "summary": {
            "total_files": len(results),
            "total_transactions": sum(result.total_transactions for result in results),
            "exported_transactions": (
                len(transactions)
                if exported_transactions is None
                else exported_transactions
            ),
            "duplicates_skipped": sum(
                result.duplicates_skipped for result in results
            ),
            "transfers_detected": sum(
                1
                for transaction in transactions
                if transaction.status == TransactionStatus.TRANSFER
            ),
            "failed_files": sum(1 for result in results if result.errors),
        },
        "by_bank": by_bank,
        "date_range": calculate_date_range(transactions),
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

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def calculate_date_range(transactions: List[Transaction]) -> dict:
    """Calculate earliest and latest transaction dates."""
    if not transactions:
        return {"earliest": None, "latest": None}

    dates = sorted(transaction.transaction_date for transaction in transactions)
    return {
        "earliest": dates[0].isoformat(),
        "latest": dates[-1].isoformat(),
    }
