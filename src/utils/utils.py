import csv
from datetime import date
from decimal import Decimal
from typing import List

from src.models.account import CrawledFile
from src.models.transactions import Transaction, TransactionStatus, TransactionType


def consolidate_files_by_bank(files: List[CrawledFile]) -> dict:
    bank_files = {'HDFC': [], 'SBI': [], 'AXIS': [], 'UNKNOWN': []}
    for file in files:
        name = file.filename.upper()
        if 'HDFC' in name:
            bank_files['HDFC'].append(file)
        elif 'SBI' in name:
            bank_files['SBI'].append(file)
        elif 'AXIS' in name:
            bank_files['AXIS'].append(file)
        else:
            bank_files['UNKNOWN'].append(file)
    return bank_files


def load_transactions_from_goodbudget_csv(csv_path: str) -> list[Transaction]:
    transactions: list[Transaction] = []
    with open(csv_path, newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        transaction_date = date.fromisoformat(row.get("transaction_date") or row["Date"])
        transaction_type = TransactionType((row.get("transaction_type") or "").lower() or "debit")
        amount = abs(Decimal(str(row.get("amount") or row.get("Amount") or "0")))
        status_raw = (row.get("status") or row.get("Status") or "").lower()
        status = (
            TransactionStatus.TRANSFER
            if status_raw == TransactionStatus.TRANSFER.value
            else TransactionStatus.PENDING
        )
        transactions.append(
            Transaction(
                transaction_date=transaction_date,
                description=row.get("description") or row.get("Name") or "",
                amount=amount,
                transaction_type=transaction_type,
                source_bank=row.get("source_bank") or row.get("Account") or "UNKNOWN",
                source_file=row.get("source_file") or "",
                balance=Decimal(row["balance"]) if row.get("balance") else None,
                status=status,
                notes=row.get("notes") or row.get("Notes"),
            )
        )

    return transactions
