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
    exported_count: int
    duplicates_by_source: dict[str, int]
    transactions_by_source: dict[str, list[Transaction]]

    @property
    def duplicates_skipped(self) -> int:
        return sum(self.duplicates_by_source.values())


def consolidate_transactions(
    all_transactions: list[Transaction],
    *,
    include_internal_transfers: bool,
) -> ConsolidationResult:
    """Dedupe overlapping statements, detect transfers and filter for export."""
    deduplicated_transactions, duplicates_by_source = deduplicate(all_transactions)
    deduplicated_transactions = detect_transfers(deduplicated_transactions)
    transactions_by_source: dict[str, list[Transaction]] = {}
    for transaction in deduplicated_transactions:
        transactions_by_source.setdefault(transaction.source_file, []).append(transaction)
    export_transactions = filter_transactions_for_export(deduplicated_transactions, include_internal_transfers)
    return ConsolidationResult(
        deduplicated_transactions=deduplicated_transactions,
        export_transactions=export_transactions,
        exported_count=len(export_transactions),
        duplicates_by_source=duplicates_by_source,
        transactions_by_source=transactions_by_source,
    )


def apply_processing_metrics(results: list[ProcessingResult], consolidation: ConsolidationResult) -> None:
    """Overwrite each file's result with its post-dedup transactions and duplicate count (mutates ``results``)."""
    for result in results:
        result.duplicates_skipped = consolidation.duplicates_by_source.get(result.source_file, 0)
        result.transactions = consolidation.transactions_by_source.get(result.source_file, [])
        result.successful = len(result.transactions)
