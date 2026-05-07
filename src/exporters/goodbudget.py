from typing import List
from pathlib import Path
import csv
from src.models.transactions import Transaction, TransactionStatus


def export_to_goodbudget(transactions: List[Transaction], output_path: str, config: dict) -> None:
    out_dir = Path(output_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    goodbudget_fields = ['Date', 'Envelope', 'Account', 'Name', 'Notes', 'Amount', 'Status']
    dashboard_fields = [
        'transaction_date', 'description', 'amount', 'transaction_type',
        'source_bank', 'source_file', 'balance', 'status', 'notes',
    ]

    max_len = config.get('export', {}).get('goodbudget', {}).get('max_description_length', 50)
    dashboard_path = out_dir / 'dashboard_data.csv'

    with open(output_path, 'w', newline='') as goodbudget_f, open(dashboard_path, 'w', newline='') as dashboard_f:
        goodbudget_writer = csv.DictWriter(goodbudget_f, fieldnames=goodbudget_fields)
        dashboard_writer = csv.DictWriter(dashboard_f, fieldnames=dashboard_fields)
        goodbudget_writer.writeheader()
        dashboard_writer.writeheader()

        for txn in transactions:
            row = format_goodbudget_row(txn, config, max_len)
            goodbudget_writer.writerow({k: row[k] for k in goodbudget_fields})
            dashboard_writer.writerow({k: row[k] for k in dashboard_fields})


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
        'status': txn_status,
        'notes': transaction.notes or '',
        # dashboard-readable alias
        'amount': str(transaction.signed_amount),
    }
