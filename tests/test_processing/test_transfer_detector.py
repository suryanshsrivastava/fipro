from datetime import date
from decimal import Decimal

from src.core.transfer_detector import detect_transfers
from src.models.transactions import Transaction, TransactionStatus, TransactionType


def make_transaction(bank: str, txn_type: TransactionType, amount: str = "1000.00") -> Transaction:
    return Transaction(
        transaction_date=date(2025, 1, 15),
        description=f"{bank} {txn_type.value}",
        amount=Decimal(amount),
        transaction_type=txn_type,
        source_bank=bank,
        source_file=f"{bank.lower()}.xls",
    )


def test_detect_transfers_marks_one_to_one_pairs():
    debit_a = make_transaction("HDFC", TransactionType.DEBIT)
    debit_b = make_transaction("SBI", TransactionType.DEBIT)
    credit_a = make_transaction("AXIS", TransactionType.CREDIT)

    flagged = detect_transfers([debit_a, debit_b, credit_a])

    statuses = [txn.status for txn in flagged]
    assert statuses.count(TransactionStatus.TRANSFER) == 2
    assert any(txn.status == TransactionStatus.PENDING for txn in flagged)


def test_detect_transfers_does_not_match_same_bank_transactions():
    debit = make_transaction("HDFC", TransactionType.DEBIT)
    credit = make_transaction("HDFC", TransactionType.CREDIT)

    flagged = detect_transfers([debit, credit])

    assert all(txn.status == TransactionStatus.PENDING for txn in flagged)
