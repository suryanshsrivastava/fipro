from pathlib import Path
from typing import List, Set, Tuple
from src.models.transactions import Transaction


def deduplicate(transactions: List[Transaction], seen_hashes: Set[str] = None) -> Tuple[List[Transaction], int]:
    if seen_hashes is None:
        seen_hashes = set()
    unique: List[Transaction] = []
    skipped = 0
    for txn in transactions:
        if txn.hash in seen_hashes:
            skipped += 1
        else:
            seen_hashes.add(txn.hash)
            unique.append(txn)
    return unique, skipped


def get_seen_hashes_from_file(filepath: str) -> Set[str]:
    try:
        with open(filepath) as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def save_seen_hashes_to_file(hashes: Set[str], filepath: str) -> None:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w') as f:
        for h in sorted(hashes):
            f.write(h + '\n')
