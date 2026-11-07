"""Spot monthly recurring payments: one similar payment to the same counterparty, on about the same day,
in 3+ consecutive months. Frequent merchants (several orders a month) are therefore not recurring."""

from collections import defaultdict
from decimal import Decimal
from statistics import median

from src.models.transactions import Transaction, TransactionType

MIN_MONTHS = 3
DAY_TOLERANCE = 5  # days from the counterparty's median day of month
AMOUNT_TOLERANCE = Decimal("0.1")  # within 10% of the counterparty's median debit


def detect_monthly(transactions: list[Transaction]) -> set[str]:
    """Hashes of debits that belong to a monthly run."""
    by_counterparty: dict[str, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        if txn.counterparty and txn.transaction_type == TransactionType.DEBIT:
            by_counterparty[txn.counterparty].append(txn)

    recurring: set[str] = set()
    for txns in by_counterparty.values():
        typical = median(abs(t.amount) for t in txns)
        similar = [t for t in txns if abs(abs(t.amount) - typical) <= typical * AMOUNT_TOLERANCE]
        usual_day = median(t.transaction_date.day for t in similar) if similar else 0
        by_month: dict[int, list[Transaction]] = defaultdict(list)
        for t in similar:
            if abs(t.transaction_date.day - usual_day) > DAY_TOLERANCE:
                continue
            by_month[t.transaction_date.year * 12 + t.transaction_date.month].append(t)
        by_month = {m: ts for m, ts in by_month.items() if len(ts) == 1}
        run: list[int] = []
        for month in sorted(by_month) + [-1]:
            if run and month != run[-1] + 1:
                if len(run) >= MIN_MONTHS:
                    recurring.update(t.hash for m in run for t in by_month[m])
                run = []
            run.append(month)
    return recurring
