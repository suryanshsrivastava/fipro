"""Times of day for bank rows, taken from the bank's UPI alert emails.

Statements carry only a date. The alert email for a UPI payment names the same 12-digit reference as the
statement narration and arrives seconds after the payment, so its received time stands in for the
payment time. ``corpus/state/txn_times.csv`` maps reference -> ``YYYY-MM-DD HH:MM`` (written by
``fipro gmail --alerts``).
"""

import csv
import os
import re
from datetime import datetime
from pathlib import Path

from src.models.transactions import Transaction

_REFERENCE = re.compile(r"(?<!\d)(\d{12})(?!\d)")
_FIELDS = ("reference", "time")


def load_txn_times(path: str) -> dict[str, str]:
    if not Path(path).exists():
        return {}
    with open(path, newline="") as f:
        return {row["reference"]: row["time"] for row in csv.DictReader(f) if row.get("reference") and row.get("time")}


def save_txn_times(new: dict[str, str], path: str) -> int:
    """Merge ``new`` into the file atomically; returns how many references were not there before."""
    stored = load_txn_times(path)
    added = len(new.keys() - stored.keys())
    stored.update(new)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(path).with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(_FIELDS)
        writer.writerows(sorted(stored.items()))
    os.replace(tmp, path)
    return added


def apply_txn_times(transactions: list[Transaction], path: str) -> int:
    """Set the time on rows whose narration holds a known reference and whose date agrees; returns how many."""
    times = load_txn_times(path)
    if not times:
        return 0
    matched = 0
    for txn in transactions:
        if txn.time:
            continue
        for ref in _REFERENCE.findall(txn.description):
            stamp = times.get(ref)
            if stamp and abs((datetime.fromisoformat(stamp).date() - txn.transaction_date).days) <= 1:
                txn.raw_data = {**(txn.raw_data or {}), "time": stamp[11:16]}
                matched += 1
                break
    return matched
