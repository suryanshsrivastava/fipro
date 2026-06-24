"""Goodbudget exporter tests."""

import csv
from datetime import date
from decimal import Decimal

from src.exporters.goodbudget import build_goodbudget_notes, export_dashboard_data, format_goodbudget_row
from src.models.transactions import Transaction, TransactionStatus, TransactionType


def _transaction(
    description: str,
    txn_type: TransactionType,
    notes: str | None = None,
    status: TransactionStatus = TransactionStatus.PENDING,
) -> Transaction:
    return Transaction(
        transaction_date=date(2025, 1, 5),
        description=description,
        amount=Decimal("500.00"),
        transaction_type=txn_type,
        source_bank="HDFC",
        source_file="sample.xls",
        notes=notes,
        status=status,
    )


def test_build_goodbudget_notes_includes_transfer_and_external_account():
    transaction = _transaction(
        "Credit card payment via CRED",
        TransactionType.DEBIT,
        notes="Existing note",
        status=TransactionStatus.TRANSFER,
    )
    transaction.external_account_name = "CREDIT_CARD"

    assert build_goodbudget_notes(transaction) == (
        "Existing note | Internal transfer detected | External account payment: CREDIT_CARD"
    )


def test_format_goodbudget_row_uses_built_notes():
    transaction = _transaction("CREDIT CARD PAYMENT", TransactionType.DEBIT)
    transaction.external_account_name = "CREDIT_CARD"

    row = format_goodbudget_row(transaction, {}, max_len=50)

    assert row["Notes"] == "External account payment: CREDIT_CARD"


def test_export_dashboard_data_uses_rich_columns(tmp_path):
    transaction = _transaction("CREDIT CARD PAYMENT", TransactionType.DEBIT)
    transaction.external_account_name = "CREDIT_CARD"
    output = tmp_path / "dashboard_data.csv"

    export_dashboard_data([transaction], str(output))

    with output.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert list(rows[0].keys()) == [
        "transaction_date",
        "description",
        "amount",
        "transaction_type",
        "source_bank",
        "source_file",
        "status",
        "notes",
        "balance",
    ]
    assert rows[0]["source_file"] == "sample.xls"
    assert rows[0]["notes"] == "External account payment: CREDIT_CARD"
