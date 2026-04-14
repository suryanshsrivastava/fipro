from typing import List
from pathlib import Path
import csv
from src.models.transactions import Transaction, TransactionStatus


def export_to_goodbudget(transactions: List[Transaction], output_path: str, config: dict) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    # Include both Goodbudget-standard cols + dashboard-readable cols
    fieldnames = [
        'Date', 'Envelope', 'Account', 'Name', 'Notes', 'Amount', 'Status',
        'transaction_date', 'description', 'amount', 'transaction_type',
        'source_bank', 'source_file', 'balance',
    ]
    max_len = config.get('export', {}).get('goodbudget', {}).get('max_description_length', 50)
    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for txn in transactions:
            row = format_goodbudget_row(txn, config, max_len)
            writer.writerow(row)


def format_goodbudget_row(transaction: Transaction, config: dict, max_len: int = 50) -> dict:
    envelope = config.get('export', {}).get('goodbudget', {}).get('default_envelope', 'Unallocated')
    status = config.get('export', {}).get('goodbudget', {}).get('default_status', 'cleared')
    txn_status = 'internal_transfer' if transaction.status == TransactionStatus.TRANSFER else status
    return {
        'Date': transaction.transaction_date.strftime('%Y-%m-%d'),
        'Envelope': transaction.envelope or envelope,
        'Account': transaction.source_bank,
        'Name': transaction.description[:max_len],
        'Notes': transaction.notes or '',
        'Amount': str(transaction.signed_amount),
        'Status': txn_status,
        # dashboard-readable cols
        'transaction_date': transaction.transaction_date.strftime('%Y-%m-%d'),
        'description': transaction.description,
        'transaction_type': transaction.transaction_type.value,
        'source_bank': transaction.source_bank,
        'source_file': transaction.source_file,
        'balance': str(transaction.balance) if transaction.balance else '',
        # dashboard-readable alias
        'amount': str(transaction.signed_amount),
    }
