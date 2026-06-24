"""External account payment detector tests."""

from datetime import date
from decimal import Decimal

from src.core.external_account_detector import detect_external_account_payments
from src.models.transactions import Transaction, TransactionType


def _transaction(description: str, txn_type: TransactionType = TransactionType.DEBIT) -> Transaction:
    return Transaction(
        transaction_date=date(2025, 1, 5),
        description=description,
        amount=Decimal("500.00"),
        transaction_type=txn_type,
        source_bank="HDFC",
        source_file="hdfc.xlsx",
    )


def test_detect_external_account_payments_marks_matching_debits():
    transaction = _transaction("Credit card payment via CRED")

    detect_external_account_payments(
        [transaction],
        {
            "external_accounts": {
                "names": ["CREDIT_CARD"],
                "payment_keywords": ["CREDIT CARD", "CRED"],
            }
        },
    )

    assert transaction.external_account_name == "CREDIT_CARD"


def test_detect_external_account_payments_ignores_credits():
    transaction = _transaction("Credit card payment refund", txn_type=TransactionType.CREDIT)

    detect_external_account_payments(
        [transaction],
        {
            "external_accounts": {
                "names": ["CREDIT_CARD"],
                "payment_keywords": ["CREDIT CARD", "CRED"],
            }
        },
    )

    assert transaction.external_account_name is None


def test_detect_external_account_payments_noop_when_config_empty():
    transaction = _transaction("CREDIT CARD PAYMENT")

    detect_external_account_payments([transaction], {})

    assert transaction.external_account_name is None
