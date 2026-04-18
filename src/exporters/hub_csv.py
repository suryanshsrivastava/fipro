"""Hub summary CSV: one row per bank with cash-flow totals."""

import csv
from decimal import Decimal
from pathlib import Path
from typing import List

from src.models.transactions import Transaction, TransactionType


def export_hub_csv(
    transactions: List[Transaction],
    output_path: str,
) -> int:
    """Write per-bank debit/credit/net totals. Returns row count (banks)."""
    by_bank: dict[str, dict[str, Decimal]] = {}

    for t in transactions:
        bucket = by_bank.setdefault(
            t.source_bank,
            {"total_credits": Decimal("0"), "total_debits": Decimal("0")},
        )
        if t.transaction_type == TransactionType.CREDIT:
            bucket["total_credits"] += abs(t.amount)
        else:
            bucket["total_debits"] += abs(t.amount)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows_written = 0
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "Bank",
                "TotalCredits",
                "TotalDebits",
                "NetCashFlow",
            ],
        )
        writer.writeheader()
        for bank in sorted(by_bank.keys()):
            b = by_bank[bank]
            net = b["total_credits"] - b["total_debits"]
            writer.writerow(
                {
                    "Bank": bank,
                    "TotalCredits": str(b["total_credits"]),
                    "TotalDebits": str(b["total_debits"]),
                    "NetCashFlow": str(net),
                }
            )
            rows_written += 1
    return rows_written
