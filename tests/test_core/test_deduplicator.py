"""Deduplicator tests."""

from datetime import date
from decimal import Decimal

from src.core.deduplicator import deduplicate
from src.models.transactions import Transaction, TransactionType


def _transaction(description: str, source_file: str = "sample.xls") -> Transaction:
    return Transaction(
        transaction_date=date(2025, 1, 1),
        description=description,
        amount=Decimal("100.00"),
        transaction_type=TransactionType.DEBIT,
        source_bank="HDFC",
        source_file=source_file,
    )


def test_deduplicate_removes_repeated_hashes():
    first = _transaction("Test txn", "first.xls")
    second = _transaction("Test txn", "second.xls")

    deduplicated, duplicates_skipped = deduplicate([first, second])

    assert deduplicated == [first]
    assert duplicates_skipped == 1


def test_deduplicate_respects_existing_seen_hashes():
    transaction = _transaction("Seen already")

    deduplicated, duplicates_skipped = deduplicate(
        [transaction], seen_hashes={transaction.hash}
    )

    assert deduplicated == []
    assert duplicates_skipped == 1
