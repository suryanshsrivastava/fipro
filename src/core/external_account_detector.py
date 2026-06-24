"""External account payment detection for Fipro."""

from src.models.transactions import Transaction, TransactionType


def detect_external_account_payments(transactions: list[Transaction], config: dict) -> list[Transaction]:
    """Annotate debit transactions that match configured payment keywords."""
    external_accounts = config.get("external_accounts", {})
    account_names = external_accounts.get("names", [])
    payment_keywords = [keyword.upper() for keyword in external_accounts.get("payment_keywords", [])]

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
