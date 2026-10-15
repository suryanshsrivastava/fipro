"""External account payment detection for Fipro."""

from src.config import Settings
from src.models.transactions import Transaction, TransactionType


def detect_external_account_payments(transactions: list[Transaction], settings: Settings) -> list[Transaction]:
    """Annotate debit transactions that match configured payment keywords."""
    account_names = settings.external_account_names
    payment_keywords = [keyword.upper() for keyword in settings.external_payment_keywords]

    if not account_names or not payment_keywords:
        return transactions

    default_account = account_names[0]
    for transaction in transactions:
        if transaction.transaction_type != TransactionType.DEBIT:
            continue
        if transaction.external_account_name:
            continue

        description = transaction.description.upper()
        if any(keyword in description for keyword in payment_keywords):
            transaction.external_account_name = default_account

    return transactions
