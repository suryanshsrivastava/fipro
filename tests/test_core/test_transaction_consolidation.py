from datetime import date
from decimal import Decimal

from src.core.transaction_consolidation import apply_processing_metrics, consolidate_transactions
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


def test_consolidate_transactions_sets_export_and_source_metrics():
    debit = _txn(source_file="one.xls", amount="500.00", transaction_type=TransactionType.DEBIT, source_bank="HDFC")
    credit = _txn(source_file="two.xls", amount="500.00", transaction_type=TransactionType.CREDIT, source_bank="SBI")
    seen_hashes: set[str] = set()

    result = consolidate_transactions(
        [debit, credit],
        seen_hashes=seen_hashes,
        prior_seen_hashes=set(),
        include_internal_transfers=False,
    )

    assert len(result.deduplicated_transactions) == 2
    assert result.export_transactions == []
    assert result.duplicates_by_source == {}
    assert set(result.transactions_by_source.keys()) == {"one.xls", "two.xls"}


def test_apply_processing_metrics_updates_processing_results():
    processing_result = ProcessingResult(
        source_file="one.xls",
        bank="HDFC",
        total_transactions=1,
        successful=1,
        failed=0,
        duplicates_skipped=0,
        transactions=[],
        errors=[],
        warnings=[],
    )
    transaction = _txn(source_file="one.xls", amount="100.00", transaction_type=TransactionType.DEBIT)

    apply_processing_metrics(
        [processing_result],
        duplicates_by_source={"one.xls": 2},
        transactions_by_source={"one.xls": [transaction]},
    )

    assert processing_result.duplicates_skipped == 2
    assert processing_result.transactions == [transaction]
    assert processing_result.successful == 1
