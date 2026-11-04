from datetime import date
from decimal import Decimal

from src.core.recurring import detect_monthly
from src.models.transactions import Transaction, TransactionType


def _debit(day: date, amount: str, who: str = "NETFLIX") -> Transaction:
    narration = f"UPI-{who}-x@ybl-1-{day}" if who else f"CASH WITHDRAWAL {day}"
    return Transaction(day, narration, Decimal(amount), TransactionType.DEBIT, "HDFC", "f.xls")


def test_three_consecutive_months_of_similar_amounts_are_monthly():
    txns = [_debit(date(2026, m, 5), a) for m, a in ((1, "649"), (2, "649"), (3, "650"))]
    assert detect_monthly(txns) == {t.hash for t in txns}


def test_gap_in_months_or_odd_amount_breaks_the_run():
    gap = [_debit(date(2026, m, 5), "649") for m in (1, 2, 4)]
    odd = [_debit(date(2026, 1, 5), "649"), _debit(date(2026, 2, 5), "649"), _debit(date(2026, 3, 5), "3000")]
    assert detect_monthly(gap) == set()
    assert detect_monthly(odd) == set()


def test_credits_and_unnamed_counterparties_are_ignored():
    credit = [_debit(date(2026, m, 5), "100") for m in (1, 2, 3)]
    for t in credit:
        t.transaction_type = TransactionType.CREDIT
    unnamed = [_debit(date(2026, m, 5), "100", who="") for m in (1, 2, 3)]
    assert detect_monthly(credit + unnamed) == set()
