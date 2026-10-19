"""Hand-maintained labels for transactions.

The exports are rebuilt from the statements on every run, so labels live in ``corpus/state`` instead:

* ``annotations.csv`` — one row per transaction, keyed by ``Transaction.hash``.
* ``category_rules.csv`` — one row per counterparty, applied to every transaction with that counterparty.

A value set on a transaction's own annotation row wins over the counterparty rule.
"""

import csv
import os
import re
from pathlib import Path

from src.models.transactions import Transaction

ANNOTATION_FIELDS = ("review_status", "category", "need_want", "frequency", "splitwise", "notes")
RULE_FIELDS = ("category", "need_want", "frequency")
_TRUE = {"1", "true", "yes", "y"}
# Fields that take one of a fixed set of values; category and notes are free text.
LABEL_CHOICES = {
    "review_status": ("cleared", "reconciled", "waiting", "doubt"),
    "need_want": ("Need", "Want"),
    "frequency": ("Monthly", "Once"),
    "splitwise": ("yes",),
}
_HASH = re.compile(r"[0-9a-f]{16}")
_MAX_TEXT = 500


def read_table(path: str, key: str) -> dict[str, dict[str, str]]:
    """Rows of a labels CSV by ``key``; an absent file means nothing is labelled yet."""
    if not Path(path).exists():
        return {}
    with open(path, newline="") as f:
        return {row[key].strip(): row for row in csv.DictReader(f) if row.get(key, "").strip()}


def write_table(path: str, key: str, fields: tuple[str, ...], rows: dict[str, dict[str, str]]) -> None:
    """Replace the file atomically: these labels cannot be regenerated, so a crash must not truncate them."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(path).with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[key, *fields], extrasaction="ignore")
        writer.writeheader()
        writer.writerows({key: k, **row} for k, row in sorted(rows.items()))
    os.replace(tmp, path)


def set_label(path: str, txn_hash: str, field: str, value: str) -> None:
    """Set one label on one transaction ("" clears it); raises ValueError for anything unknown or out of range."""
    value = value.strip()
    if not _HASH.fullmatch(txn_hash):
        raise ValueError(f"not a transaction hash: {txn_hash!r}")
    if field not in ANNOTATION_FIELDS:
        raise ValueError(f"unknown label field: {field!r}")
    if value and field in LABEL_CHOICES and value not in LABEL_CHOICES[field]:
        raise ValueError(f"{field} must be one of {LABEL_CHOICES[field]}, not {value!r}")
    if len(value) > _MAX_TEXT:
        raise ValueError(f"{field} is longer than {_MAX_TEXT} characters")
    rows = read_table(path, "hash")
    row = rows.setdefault(txn_hash, {})
    row[field] = value
    if not any(row.get(f) for f in ANNOTATION_FIELDS):
        del rows[txn_hash]
    write_table(path, "hash", ANNOTATION_FIELDS, rows)


def overlay_labels(rows: list[dict], annotations_path: str) -> None:
    """Show labels saved since the last `fipro process` on exported rows (a row's own label wins)."""
    annotations = read_table(annotations_path, "hash")
    for row in rows:
        for field, value in annotations.get(row.get("hash", ""), {}).items():
            if field in ANNOTATION_FIELDS and value:
                row[field] = value


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
