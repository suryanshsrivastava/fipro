"""Transfer detection tests."""

from datetime import date
from decimal import Decimal

from src.core.transfer_detector import detect_transfers, is_transfer_pair
from src.models.transactions import Transaction, TransactionStatus, TransactionType


def _transaction(bank: str, txn_type: TransactionType, description: str = "txn") -> Transaction:
    return Transaction(
        transaction_date=date(2025, 1, 3),
        description=description,
        amount=Decimal("1000.00"),
        transaction_type=txn_type,
        source_bank=bank,
        source_file=f"{bank.lower()}.xls",
    )


def test_is_transfer_pair_matches_cross_bank_mirror():
    debit = _transaction("HDFC", TransactionType.DEBIT)
    credit = _transaction("SBI", TransactionType.CREDIT)

    assert is_transfer_pair(debit, credit) is True


def test_is_transfer_pair_rejects_same_bank_mirror():
    debit = _transaction("HDFC", TransactionType.DEBIT)
    credit = _transaction("HDFC", TransactionType.CREDIT)

    assert is_transfer_pair(debit, credit) is False


def test_detect_transfers_marks_both_transactions():
    debit = _transaction("HDFC", TransactionType.DEBIT)
    credit = _transaction("SBI", TransactionType.CREDIT)

    detect_transfers([debit, credit])

    assert debit.status == TransactionStatus.TRANSFER
    assert credit.status == TransactionStatus.TRANSFER
