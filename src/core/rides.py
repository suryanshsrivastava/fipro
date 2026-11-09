"""Uber and Rapido trip receipts, matched to the bank rows that paid for them.

Receipts are read from email (``corpus/state/rides.csv`` holds one row per trip). A payment to a driver
looks like any UPI payment to a person, so a trip receipt is the evidence that it was a cab ride:

* Rapido: the captain's name is in both the receipt and the narration, the fare matches, the day matches.
* Uber: the fare (total or suggested fare) matches and the day matches, and the narration names the driver or Uber.

A trip with no matching row is normal (someone else paid, or cash); it stays in the list, unmatched.
"""

import csv
import os
import re
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src.models.transactions import Transaction, TransactionType

RIDE_FIELDS = ("provider", "day", "time", "fare", "fare_alt", "driver", "paid_with")
RIDE_CATEGORY = "City/Cab"
_MONEY = r"₹\s*([\d,]+(?:\.\d+)?)"
_RAPIDO_TIME = re.compile(r"Time of Ride\s+([A-Z][a-z]{2}) (\d{1,2})(?:st|nd|rd|th) (\d{4}), (\d{1,2}):(\d{2}) ([AP]M)")
_UBER_START = re.compile(
    r"([A-Z][a-z]{2})[a-z]? (\d{1,2}), (\d{4})\s*,?\s*(\d{1,2}:\d{2} [ap]m)"
)  # 'Sept' as well as 'Sep'


def _num(text: str) -> str:
    return text.replace(",", "")


def parse_receipt(provider: str, text: str) -> dict[str, str] | None:
    """One trip from a receipt email's text, or None when it is not a trip receipt."""
    if provider == "rapido":
        when, fare, driver = (
            _RAPIDO_TIME.search(text),
            re.search(r"(?:Selected Price|Total(?: Amount)?)\s+" + _MONEY, text),
            re.search(r"Driver name\s+(.+?)\s+Vehicle Number", text),
        )
        if not (when and fare):
            return None
        stamp = datetime.strptime(f"{when[1]} {when[2]} {when[3]} {when[4]}:{when[5]} {when[6]}", "%b %d %Y %I:%M %p")
        return {
            "provider": "rapido",
            "day": stamp.date().isoformat(),
            "time": stamp.strftime("%H:%M"),
            "fare": _num(fare[1]),
            "fare_alt": "",
            "driver": driver[1] if driver else "",
            "paid_with": "",
        }
    if provider == "uber":
        when, total = _UBER_START.search(text), re.search(r"Total\s+" + _MONEY, text)
        if not (when and total):
            return None
        stamp = datetime.strptime(f"{when[1]} {when[2]}, {when[3]} {when[4]}", "%b %d, %Y %I:%M %p")
        suggested, driver, paid = (
            re.search(r"Suggested fare\s+" + _MONEY, text),
            re.search(r"You rode with ([A-Za-z ]+?)(?: \d\.\d+|\s{2,}|$)", text),
            re.search(r"Payments\s+(\w+)\s+" + _MONEY, text),
        )
        return {
            "provider": "uber",
            "day": stamp.date().isoformat(),
            "time": stamp.strftime("%H:%M"),
            "fare": _num(total[1]),
            "fare_alt": _num(suggested[1]) if suggested else "",
            "driver": driver[1].strip() if driver else "",
            "paid_with": paid[1] if paid else "",
        }
    return None


def load_rides(path: str) -> list[dict[str, str]]:
    if not Path(path).exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def save_rides(rides: list[dict[str, str]], path: str) -> int:
    """Merge into the file (a trip is its provider, day, time and fare); returns how many were new."""
    key = lambda r: (r["provider"], r["day"], r["time"], r["fare"])  # noqa: E731
    stored = {key(r): r for r in load_rides(path)}
    added = len({key(r) for r in rides} - stored.keys())
    stored.update({key(r): r for r in rides})
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(path).with_suffix(".tmp")
    with open(tmp, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=RIDE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(stored.values(), key=lambda r: (r["day"], r["time"])))
    os.replace(tmp, path)
    return added


def _fare_matches(ride: dict[str, str], amount: Decimal, *, named: bool) -> bool:
    """Rapido: the price agreed with the captain. Uber paid direct to a named driver: the fare rounded up or tipped.

    A payment that only says "Uber" is the app charging the exact fare, so it must match to the rupee.
    """
    fares = [Decimal(v) for v in (ride["fare"], ride["fare_alt"]) if v]
    if ride["provider"] == "rapido" or named:
        return any(
            abs(amount - f) <= max(Decimal(10), f * Decimal("0.15" if ride["provider"] == "rapido" else "0.05"))
            for f in fares
        )
    return any(abs(amount - f) <= 1 for f in fares)


def _names(text: str) -> set[str]:
    return set(re.findall(r"[a-z]{3,}", text.lower()))


def _is_match(ride: dict[str, str], txn: Transaction) -> bool:
    if txn.transaction_type != TransactionType.DEBIT or not ride["day"]:
        return False
    if abs((date.fromisoformat(ride["day"]) - txn.transaction_date).days) > 1:
        return False
    narration = txn.description.lower()
    first = (ride["driver"].split() or [""])[0].lower()
    named = len(first) >= 3 and first in _names(narration)
    if not _fare_matches(ride, txn.amount, named=named):
        return False
    return named or (ride["provider"] == "uber" and "uber" in narration)


def match_rides(transactions: list[Transaction], rides: list[dict[str, str]]) -> tuple[int, list[dict[str, str]]]:
    """Label the paying rows City/Cab with a ride note; returns (rows labelled, trips with no payment row).

    Only rows with no category yet are touched here; the user's own labels and payee rules apply afterwards and win.
    """
    used: set[int] = set()
    matched = 0
    unmatched = []
    for ride in rides:
        hit = next((t for t in transactions if id(t) not in used and not t.category and _is_match(ride, t)), None)
        if hit is None:
            unmatched.append(ride)
            continue
        used.add(id(hit))
        hit.category = RIDE_CATEGORY
        hit.notes = f"{ride['provider'].title()} ride {ride['day']} {ride['time']}, driver {ride['driver'] or '?'}, fare ₹{ride['fare']}"
        matched += 1
    return matched, unmatched
