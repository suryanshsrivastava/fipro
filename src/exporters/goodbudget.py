"""Goodbudget CSV exporter for Fipro."""

import csv
from pathlib import Path
from typing import List

from src.models.transactions import Transaction, TransactionStatus


def export_to_goodbudget(
    transactions: List[Transaction], output_path: str, config: dict
) -> int:
    """Export transactions to a Goodbudget-compatible CSV file."""
    include_internal_transfers = config.get("processing", {}).get(
        "include_internal_transfers", True
    )
    filtered = [
        transaction
        for transaction in transactions
        if include_internal_transfers
        or transaction.status != TransactionStatus.TRANSFER
    ]
    filtered.sort(
        key=lambda transaction: (
            transaction.transaction_date,
            transaction.source_bank,
            transaction.description,
        )
    )

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Date",
                "Envelope",
                "Account",
                "Name",
                "Notes",
                "Amount",
                "Status",
            ],
        )
        writer.writeheader()
        for transaction in filtered:
            writer.writerow(format_goodbudget_row(transaction, config))

    return len(filtered)


def format_goodbudget_row(transaction: Transaction, config: dict) -> dict:
    """Format a single transaction row for Goodbudget export."""
    row = transaction.to_goodbudget_row()
    row["Notes"] = _build_notes(transaction, config)
    return row


def _build_notes(transaction: Transaction, config: dict) -> str:
    notes: list[str] = []
    if transaction.notes:
        notes.append(transaction.notes)
    if transaction.status == TransactionStatus.TRANSFER:
        notes.append("Internal transfer detected")

    external_accounts = config.get("external_accounts", {})
    account_names = external_accounts.get("names", ["CREDIT_CARD"])
    payment_keywords = [
        keyword.upper() for keyword in external_accounts.get("payment_keywords", [])
    ]

    description = transaction.description.upper()
    if (
        transaction.transaction_type.value == "debit"
        and any(keyword in description for keyword in payment_keywords)
        and account_names
    ):
        notes.append(f"External account payment: {account_names[0]}")

    return " | ".join(notes)
