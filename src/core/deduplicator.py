from src.models.transactions import Transaction


def deduplicate(transactions: list[Transaction]) -> tuple[list[Transaction], dict[str, int]]:
    """Drop transactions that appear in more than one overlapping statement.

    Two rows are the same transaction when their hashes match, or when they come from different files
    with the same date, amount, type, bank and running balance and one narration is a prefix of the
    other: a statement that splits a row across a page can cut its narration short. The first row seen
    is kept, with the fuller narration.

    Returns the unique transactions and the number of duplicates dropped per source file.
    """
    unique: list[Transaction] = []
    duplicates_by_source: dict[str, int] = {}
    seen_hashes: set[str] = set()
    by_identity: dict[tuple, list[Transaction]] = {}
    for txn in transactions:
        twin = _truncated_twin(txn, by_identity)
        if txn.hash in seen_hashes or twin:
            if twin and len(txn.narration_key) > len(twin.narration_key):
                twin.description = txn.description
            duplicates_by_source[txn.source_file] = duplicates_by_source.get(txn.source_file, 0) + 1
            continue
        seen_hashes.add(txn.hash)
        by_identity.setdefault(_identity(txn), []).append(txn)
        unique.append(txn)
    return unique, duplicates_by_source


def _identity(txn: Transaction) -> tuple:
    return (txn.transaction_date, txn.amount, txn.transaction_type, txn.source_bank, txn.balance)


def _truncated_twin(txn: Transaction, by_identity: dict[tuple, list[Transaction]]) -> Transaction | None:
    """An earlier row from another file that is the same transaction with a truncated (or fuller) narration."""
    if txn.balance is None:
        return None
    for other in by_identity.get(_identity(txn), []):
        shorter, longer = sorted((txn.narration_key, other.narration_key), key=len)
        if other.source_file != txn.source_file and longer.startswith(shorter):
            return other
    return None
