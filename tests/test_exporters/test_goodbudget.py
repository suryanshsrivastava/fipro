"""Goodbudget exporter tests."""

import csv
from datetime import date
from decimal import Decimal

from src.exporters.goodbudget import export_to_goodbudget, format_goodbudget_row
from src.models.transactions import Transaction, TransactionStatus, TransactionType


def _transaction(
    description: str,
    txn_type: TransactionType,
    bank: str = "HDFC",
    notes: str | None = None,
    status: TransactionStatus = TransactionStatus.PENDING,
) -> Transaction:
    return Transaction(
        transaction_date=date(2025, 1, 5),
        description=description,
        amount=Decimal("500.00"),
        transaction_type=txn_type,
        source_bank=bank,
        source_file="sample.xls",
        notes=notes,
        status=status,
    )


def test_format_goodbudget_row_adds_transfer_and_external_account_notes():
    transaction = _transaction(
        "Credit card payment via CRED",
        TransactionType.DEBIT,
        notes="Existing note",
        status=TransactionStatus.TRANSFER,
    )
    config = {
        "external_accounts": {
            "names": ["CREDIT_CARD"],
            "payment_keywords": ["CREDIT CARD", "CRED"],
        }
    }

    row = format_goodbudget_row(transaction, config)

    assert row["Notes"] == (
        "Existing note | Internal transfer detected | "
        "External account payment: CREDIT_CARD"
    )


def test_export_to_goodbudget_keeps_transfers_when_configured(tmp_path):
    transaction = _transaction(
        "Transfer to SBI",
        TransactionType.DEBIT,
        status=TransactionStatus.TRANSFER,
    )
    output_path = tmp_path / "output.csv"

    exported_count = export_to_goodbudget(
        [transaction],
        str(output_path),
        {
            "processing": {"include_internal_transfers": True},
            "external_accounts": {"names": [], "payment_keywords": []},
        },
    )

    with output_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert exported_count == 1
    assert rows[0]["Notes"] == "Internal transfer detected"
