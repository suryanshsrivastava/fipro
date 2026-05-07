from src.models.transactions import Transaction


def deduplicate(transactions: list[Transaction], seen_hashes: set[str] | None = None) -> tuple[list[Transaction], int]:
    if seen_hashes is None:
        seen_hashes = set()
    unique: list[Transaction] = []
    skipped = 0
    for txn in transactions:
        if txn.hash in seen_hashes:
            skipped += 1
        else:
            seen_hashes.add(txn.hash)
            unique.append(txn)
    return unique, skipped


def get_seen_hashes_from_file(filepath: str) -> set[str]:
    try:
        with open(filepath) as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def save_seen_hashes_to_file(hashes: set[str], filepath: str) -> None:
    with open(filepath, "w") as f:
        for h in sorted(hashes):
            f.write(h + "\n")
