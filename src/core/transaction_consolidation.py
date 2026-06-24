from dataclasses import dataclass

from src.core.deduplicator import deduplicate
from src.core.transfer_detector import detect_transfers
from src.models.result import ProcessingResult
from src.models.transactions import Transaction
from src.utils.report_helpers import filter_transactions_for_export


@dataclass(slots=True)
class ConsolidationResult:
    deduplicated_transactions: list[Transaction]
    export_transactions: list[Transaction]
    duplicates_by_source: dict[str, int]
    transactions_by_source: dict[str, list[Transaction]]


def _count_duplicates_by_source(
    transactions: list[Transaction],
    prior_seen_hashes: set[str],
) -> dict[str, int]:
    duplicates_by_source: dict[str, int] = {}
    session_seen = set(prior_seen_hashes)
    for transaction in transactions:
        if transaction.hash in session_seen:
            duplicates_by_source[transaction.source_file] = duplicates_by_source.get(transaction.source_file, 0) + 1
            continue
        session_seen.add(transaction.hash)
    return duplicates_by_source


def _group_transactions_by_source(transactions: list[Transaction]) -> dict[str, list[Transaction]]:
    transactions_by_source: dict[str, list[Transaction]] = {}
    for transaction in transactions:
        transactions_by_source.setdefault(transaction.source_file, []).append(transaction)
    return transactions_by_source


def consolidate_transactions(
    all_transactions: list[Transaction],
    *,
    seen_hashes: set[str],
    prior_seen_hashes: set[str],
    include_internal_transfers: bool,
) -> ConsolidationResult:
    deduplicated_transactions, _ = deduplicate(all_transactions, seen_hashes)
    deduplicated_transactions = detect_transfers(deduplicated_transactions)
    duplicates_by_source = _count_duplicates_by_source(all_transactions, prior_seen_hashes)
    transactions_by_source = _group_transactions_by_source(deduplicated_transactions)
    export_transactions = filter_transactions_for_export(deduplicated_transactions, include_internal_transfers)
    return ConsolidationResult(
        deduplicated_transactions=deduplicated_transactions,
        export_transactions=export_transactions,
        duplicates_by_source=duplicates_by_source,
        transactions_by_source=transactions_by_source,
    )


def apply_processing_metrics(
    results: list[ProcessingResult],
    *,
    duplicates_by_source: dict[str, int],
    transactions_by_source: dict[str, list[Transaction]],
) -> None:
    for result in results:
        result.duplicates_skipped = duplicates_by_source.get(result.source_file, 0)
        result.transactions = transactions_by_source.get(result.source_file, [])
        result.successful = len(result.transactions)
