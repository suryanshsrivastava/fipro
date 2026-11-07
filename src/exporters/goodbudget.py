import csv
from pathlib import Path

from src.config import GoodbudgetSettings
from src.models.transactions import Transaction, TransactionStatus

GOODBUDGET_FIELDNAMES = ["Date", "Envelope", "Account", "Name", "Notes", "Amount", "Status"]
DASHBOARD_FIELDNAMES = [
    "hash",
    "transaction_date",
    "description",
    "amount",
    "transaction_type",
    "source_bank",
    "source_file",
    "status",
    "notes",
    "balance",
    "payment_mode",
    "counterparty",
    "category",
    "review_status",
    "need_want",
    "frequency",
    "splitwise",
]


def export_to_goodbudget(transactions: list[Transaction], output_path: str, settings: GoodbudgetSettings) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=GOODBUDGET_FIELDNAMES)
        writer.writeheader()
        for txn in transactions:
            row = format_goodbudget_row(txn, settings)
            writer.writerow(row)


def export_dashboard_data(transactions: list[Transaction], output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=DASHBOARD_FIELDNAMES)
        writer.writeheader()
        for txn in transactions:
            writer.writerow(
                {
                    "hash": txn.hash,
                    "transaction_date": txn.transaction_date.strftime("%Y-%m-%d"),
                    "description": txn.description,
                    "amount": str(txn.signed_amount),
                    "transaction_type": txn.transaction_type.value,
                    "source_bank": txn.source_bank,
                    "source_file": Path(txn.source_file).name,
                    "status": txn.status.value,
                    "notes": build_goodbudget_notes(txn),
                    "balance": str(txn.balance) if txn.balance is not None else "",
                    "payment_mode": txn.payment_mode,
                    "counterparty": txn.counterparty,
                    "category": txn.category or "",
                    "review_status": txn.review_status,
                    "need_want": txn.need_want,
                    "frequency": txn.frequency,
                    "splitwise": "yes" if txn.splitwise else "",
                }
            )


def format_goodbudget_row(transaction: Transaction, settings: GoodbudgetSettings) -> dict:
    status = "internal_transfer" if transaction.status == TransactionStatus.TRANSFER else settings.default_status
    return {
        "Date": transaction.transaction_date.strftime("%Y-%m-%d"),
        "Envelope": transaction.envelope or settings.default_envelope,
        "Account": transaction.source_bank,
        "Name": transaction.description[: settings.max_description_length],
        "Notes": build_goodbudget_notes(transaction),
        "Amount": str(transaction.signed_amount),
        "Status": status,
    }


def build_goodbudget_notes(transaction: Transaction) -> str:
    notes: list[str] = []
    if transaction.notes:
        notes.append(transaction.notes)
    if transaction.status == TransactionStatus.TRANSFER:
        notes.append("Internal transfer detected")
    if transaction.external_account_name:
        notes.append(f"External account payment: {transaction.external_account_name}")
    return " | ".join(notes)
