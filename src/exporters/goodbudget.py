import csv
from pathlib import Path

from src.models.transactions import Transaction, TransactionStatus

GOODBUDGET_FIELDNAMES = ["Date", "Envelope", "Account", "Name", "Notes", "Amount", "Status"]


def export_to_goodbudget(transactions: list[Transaction], output_path: str, config: dict) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    max_len = config.get("export", {}).get("goodbudget", {}).get("max_description_length", 50)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=GOODBUDGET_FIELDNAMES)
        writer.writeheader()
        for txn in transactions:
            row = format_goodbudget_row(txn, config, max_len)
            writer.writerow(row)


def format_goodbudget_row(transaction: Transaction, config: dict, max_len: int = 50) -> dict:
    envelope = config.get("export", {}).get("goodbudget", {}).get("default_envelope", "Unallocated")
    status = config.get("export", {}).get("goodbudget", {}).get("default_status", "cleared")
    txn_status = "internal_transfer" if transaction.status == TransactionStatus.TRANSFER else status
    return {
        "Date": transaction.transaction_date.strftime("%Y-%m-%d"),
        "Envelope": transaction.envelope or envelope,
        "Account": transaction.source_bank,
        "Name": transaction.description[:max_len],
        "Notes": build_goodbudget_notes(transaction),
        "Amount": str(transaction.signed_amount),
        "Status": txn_status,
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
