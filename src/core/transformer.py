from typing import List
from datetime import date
from decimal import Decimal
from src.models.transactions import Transaction, TransactionType
from src.utils.date_parser import parse_date_multiple_formats
from src.utils.amount_parser import parse_amount

BANK_DATE_FORMATS = {
    'HDFC': ['%d/%m/%y', '%d-%m-%Y'],
    'SBI': ['%d %b %Y'],
    'AXIS': ['%d-%m-%Y'],
}


def clean_transactions(raw_transactions: List[dict], bank: str, source_file: str) -> List[Transaction]:
    result = []
    for raw in raw_transactions:
        try:
            txn_date = standardize_date(raw.get('transaction_date', ''), bank, {})
            description = clean_description(str(raw.get('description', '')))
            amount = standardize_amount(raw.get('amount', '0'))
            txn_type = TransactionType(raw.get('transaction_type', 'debit'))
            result.append(Transaction(
                transaction_date=txn_date,
                description=description,
                amount=amount,
                transaction_type=txn_type,
                source_bank=bank,
                source_file=source_file,
            ))
        except Exception:
            continue
    return result


def clean_description(description: str) -> str:
    return ' '.join(description.split()).strip()


def standardize_date(date_str: str, bank: str, config: dict) -> date:
    formats = BANK_DATE_FORMATS.get(bank, ['%d-%m-%Y', '%d/%m/%y'])
    parsed = parse_date_multiple_formats(date_str, formats)
    if parsed is None:
        raise ValueError(f'Unable to parse date: {date_str}')
    return parsed


def standardize_amount(amount_str: str) -> Decimal:
    return parse_amount(amount_str)
