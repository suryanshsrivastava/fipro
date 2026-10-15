"""Processing report generator for Fipro."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.models.result import HubSummary, PipelineRun, ProcessingResult
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
    include_internal_transfers: bool = True,
    duplicates_skipped: int = 0,
    transactions: list[Transaction] | None = None,
    export_transactions: list[Transaction] | None = None,
) -> tuple[dict, HubSummary]:
    """Generate and write a JSON processing report; returns the report and its hub summary.

    ``transactions`` and ``export_transactions`` default to the results' transactions and
    the ``include_internal_transfers`` export filter respectively.
    """
    if transactions is None:
        transactions = [transaction for result in results for transaction in result.transactions]
    if export_transactions is None:
        export_transactions = filter_transactions_for_export(transactions, include_internal_transfers)

    by_bank: dict[str, dict[str, int]] = {}
    for transaction in export_transactions:
        bank_bucket = by_bank.setdefault(
            transaction.source_bank,
            {"transactions": 0, "debits": 0, "credits": 0},
        )
        bank_bucket["transactions"] += 1
        if transaction.transaction_type == TransactionType.DEBIT:
            bank_bucket["debits"] += 1
        else:
            bank_bucket["credits"] += 1

    date_range = calculate_date_range(export_transactions)
    ending_balances = ending_balances_by_statement(export_transactions)

    report = {
        "run_id": datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
        "summary": {
            "total_files": len(results),
            "total_transactions": sum(result.total_transactions for result in results),
            "exported_transactions": len(export_transactions),
            "duplicates_skipped": duplicates_skipped,
            "transfers_detected": sum(
                1 for transaction in transactions if transaction.status == TransactionStatus.TRANSFER
            ),
            "failed_files": sum(1 for result in results if result.errors),
        },
        "by_bank": by_bank,
        "date_range": date_range,
        "cash_flow": cash_flow_from_transactions(export_transactions),
        "net_worth_proxy": ending_balances,
        "top_descriptions": top_descriptions(export_transactions),
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
            key=lambda item: str(item["source_file"]),
        ),
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report, HubSummary.from_report(report)


def calculate_date_range(transactions: list[Transaction]) -> dict:
    """Calculate earliest and latest transaction dates."""
    if not transactions:
        return {"earliest": None, "latest": None}

    dates = sorted(transaction.transaction_date for transaction in transactions)
    return {
        "earliest": dates[0].isoformat(),
        "latest": dates[-1].isoformat(),
    }


def summarize_pipeline_run(run: PipelineRun) -> list[str]:
    """Format CLI lines from a completed pipeline run."""
    if not run.results:
        return ["No input files found."]

    parsed_count = sum(result.total_transactions for result in run.results)
    exported_count = run.exported_count
    failed = sum(len(result.errors) for result in run.results)
    lines = [
        (
            f"Processed {len(run.results)} file(s): "
            f"{parsed_count} parsed, {exported_count} exported after dedup, {failed} error(s)."
        )
    ]

    summary = run.hub_summary
    if summary.earliest and summary.latest:
        lines.append(f"Statement window: {summary.earliest} to {summary.latest}")

    if summary.cash_flow and summary.cash_flow.get("net_cash_flow") is not None:
        lines.append(f"Net cash flow (export scope): {summary.cash_flow['net_cash_flow']}")

    if summary.total_across_statements is not None:
        lines.append(f"Statement balances sum (not net worth): {summary.total_across_statements}")

    if run.locked_files:
        lines.append(
            f"{len(run.locked_files)} password-protected file(s) left in input; unlock them in `fipro dashboard`:"
        )
        lines.extend(f"  - {Path(path).name}" for path in run.locked_files)

    return lines
