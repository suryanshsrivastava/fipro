from src.models.transactions import Transaction


def deduplicate(
    transactions: list[Transaction], seen_hashes: set[str] | None = None
) -> tuple[list[Transaction], dict[str, int]]:
    """Drop transactions whose hash is already in ``seen_hashes`` (which is updated in place).

    Callers that re-read the whole corpus each run pass a fresh set, so only duplicates within that run
    are dropped — the same transaction appearing in two overlapping statements.

    A truncated copy also counts as a duplicate: a statement that splits a row across a page can cut its
    narration short, so the same transaction hashes differently in two overlapping files. Rows from
    different files with the same date, amount, type, bank and running balance whose narrations are
    prefix-related are the same transaction, and the fuller narration is kept.

    Returns the unique transactions and the number of duplicates dropped per source file.
    """
    if seen_hashes is None:
        seen_hashes = set()
    unique: list[Transaction] = []
    duplicates_by_source: dict[str, int] = {}
    by_identity: dict[tuple, list[int]] = {}
    for txn in transactions:
        if txn.hash in seen_hashes:
            duplicates_by_source[txn.source_file] = duplicates_by_source.get(txn.source_file, 0) + 1
            continue
        twin = _truncated_twin(txn, unique, by_identity)
        if twin is None:
            seen_hashes.add(txn.hash)
            by_identity.setdefault(_identity(txn), []).append(len(unique))
            unique.append(txn)
            continue
        dropped = txn
        if len(_narration(txn)) > len(_narration(unique[twin])):
            dropped, unique[twin] = unique[twin], txn
            seen_hashes.add(txn.hash)
        duplicates_by_source[dropped.source_file] = duplicates_by_source.get(dropped.source_file, 0) + 1
    return unique, duplicates_by_source


def _narration(txn: Transaction) -> str:
    return "".join(txn.description.split())


def _identity(txn: Transaction) -> tuple:
    return (txn.transaction_date, txn.amount, txn.transaction_type, txn.source_bank, txn.balance)


def _truncated_twin(txn: Transaction, unique: list[Transaction], by_identity: dict[tuple, list[int]]) -> int | None:
    """Index in ``unique`` of an earlier row from another file that is a truncated copy of ``txn`` (or vice versa)."""
    if txn.balance is None:
        return None
    mine = _narration(txn)
    for i in by_identity.get(_identity(txn), []):
        other = unique[i]
        theirs = _narration(other)
        if other.source_file != txn.source_file and (mine.startswith(theirs) or theirs.startswith(mine)):
            return i
    return None
