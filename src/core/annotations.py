"""Hand-maintained labels for transactions.

The exports are rebuilt from the statements on every run, so labels live in ``corpus/state`` instead:

* ``annotations.csv`` — one row per transaction, keyed by ``Transaction.hash``.
* ``category_rules.csv`` — one row per counterparty, applied to every transaction with that counterparty.

A value set on a transaction's own annotation row wins over the counterparty rule.
"""

import csv
from pathlib import Path

from src.models.transactions import Transaction

ANNOTATION_FIELDS = ("review_status", "category", "need_want", "frequency", "splitwise", "notes")
RULE_FIELDS = ("category", "need_want", "frequency")
_TRUE = {"1", "true", "yes", "y"}


def read_table(path: str, key: str) -> dict[str, dict[str, str]]:
    """Rows of a labels CSV by ``key``; an absent file means nothing is labelled yet."""
    if not Path(path).exists():
        return {}
    with open(path, newline="") as f:
        return {row[key].strip(): row for row in csv.DictReader(f) if row.get(key, "").strip()}


def write_table(path: str, key: str, fields: tuple[str, ...], rows: dict[str, dict[str, str]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[key, *fields], extrasaction="ignore")
        writer.writeheader()
        writer.writerows({key: k, **row} for k, row in sorted(rows.items()))


def apply_annotations(transactions: list[Transaction], annotations_path: str, rules_path: str) -> None:
    annotations = read_table(annotations_path, "hash")
    rules = {name.upper(): row for name, row in read_table(rules_path, "counterparty").items()}
    for txn in transactions:
        own = annotations.get(txn.hash, {})
        rule = rules.get(txn.counterparty, {}) if txn.counterparty else {}
        txn.category = own.get("category") or rule.get("category") or None
        txn.need_want = own.get("need_want") or rule.get("need_want") or ""
        txn.frequency = own.get("frequency") or rule.get("frequency") or ""
        txn.review_status = own.get("review_status", "")
        txn.splitwise = own.get("splitwise", "").strip().lower() in _TRUE
        if own.get("notes"):
            txn.notes = own["notes"]
