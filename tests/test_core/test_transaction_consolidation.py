from datetime import date
from decimal import Decimal

from src.core.transaction_consolidation import consolidate_transactions
from src.models.result import ProcessingResult
from src.models.transactions import Transaction, TransactionType


def _txn(
    *,
    source_file: str,
    amount: str,
    transaction_type: TransactionType,
    source_bank: str = "HDFC",
    description: str = "txn",
) -> Transaction:
    return Transaction(
        transaction_date=date(2026, 1, 1),
        description=description,
        amount=Decimal(amount),
        transaction_type=transaction_type,
        source_bank=source_bank,
        source_file=source_file,
    )


def _result(source_file: str) -> ProcessingResult:
    return ProcessingResult(
        source_file=source_file,
        bank="HDFC",
        total_transactions=1,
        successful=1,
        failed=0,
        duplicates_skipped=0,
        transactions=[],
        errors=[],
        warnings=[],
    )


def test_consolidate_transactions_sets_export_and_source_metrics():
    debit = _txn(source_file="one.xls", amount="500.00", transaction_type=TransactionType.DEBIT, source_bank="HDFC")
    credit = _txn(source_file="two.xls", amount="500.00", transaction_type=TransactionType.CREDIT, source_bank="SBI")
    results = [_result("one.xls"), _result("two.xls")]

    consolidated = consolidate_transactions(
        [debit, credit],
        seen_hashes=set(),
        prior_seen_hashes=set(),
        include_internal_transfers=False,
        results=results,
    )

    assert len(consolidated.deduplicated_transactions) == 2
    assert consolidated.export_transactions == []
    assert consolidated.exported_count == 0
    assert consolidated.duplicates_skipped == 0
    assert [r.transactions for r in results] == [[debit], [credit]]


def test_consolidate_transactions_counts_prior_duplicates_per_file():
    txn = _txn(source_file="one.xls", amount="100.00", transaction_type=TransactionType.DEBIT)
    results = [_result("one.xls")]

    consolidated = consolidate_transactions(
        [txn],
        seen_hashes={txn.hash},
        prior_seen_hashes={txn.hash},
        include_internal_transfers=True,
        results=results,
    )

    assert consolidated.duplicates_skipped == 1
    assert results[0].duplicates_skipped == 1
    assert results[0].successful == 0
