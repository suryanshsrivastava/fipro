from pathlib import Path

from src.models.transactions import Transaction


def deduplicate(
    transactions: list[Transaction], seen_hashes: set[str] | None = None
) -> tuple[list[Transaction], dict[str, int]]:
    """Drop transactions whose hash is already in ``seen_hashes`` (which is updated in place).

    Returns the unique transactions and the number of duplicates dropped per source file.
    """
    if seen_hashes is None:
        seen_hashes = set()
    unique: list[Transaction] = []
    duplicates_by_source: dict[str, int] = {}
    for txn in transactions:
        if txn.hash in seen_hashes:
            duplicates_by_source[txn.source_file] = duplicates_by_source.get(txn.source_file, 0) + 1
        else:
            seen_hashes.add(txn.hash)
            unique.append(txn)
    return unique, duplicates_by_source


def get_seen_hashes_from_file(filepath: str) -> set[str]:
    try:
        with open(filepath) as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def save_seen_hashes_to_file(hashes: set[str], filepath: str) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for h in sorted(hashes):
            f.write(h + "\n")
