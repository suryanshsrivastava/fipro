"""Hub CSV exporter tests."""

from datetime import date
from decimal import Decimal
import csv

from src.exporters.hub_csv import export_hub_csv
from src.models.transactions import Transaction, TransactionType


def test_export_hub_csv_per_bank_totals(tmp_path):
    transactions = [
        Transaction(
            transaction_date=date(2025, 1, 1),
            description="A",
            amount=Decimal("100.00"),
            transaction_type=TransactionType.CREDIT,
            source_bank="HDFC",
            source_file="a.xls",
        ),
        Transaction(
            transaction_date=date(2025, 1, 2),
            description="B",
            amount=Decimal("40.00"),
            transaction_type=TransactionType.DEBIT,
            source_bank="HDFC",
            source_file="a.xls",
        ),
        Transaction(
            transaction_date=date(2025, 1, 3),
            description="C",
            amount=Decimal("10.00"),
            transaction_type=TransactionType.DEBIT,
            source_bank="SBI",
            source_file="b.xls",
        ),
    ]
    path = tmp_path / "hub.csv"
    export_hub_csv(transactions, str(path))
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    by_bank = {r["Bank"]: r for r in rows}
    assert by_bank["HDFC"]["NetCashFlow"] == "60.00"
    assert by_bank["SBI"]["NetCashFlow"] == "-10.00"
