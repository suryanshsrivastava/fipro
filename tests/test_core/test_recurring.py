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


def test_detected_frequency_is_flagged_and_own_label_is_not(tmp_path):
    from src.core.annotations import apply_annotations, set_label

    txns = [_debit(date(2026, m, 5), "649") for m in (1, 2, 3)]
    ann, rules = str(tmp_path / "a.csv"), str(tmp_path / "r.csv")
    set_label(ann, txns[0].hash, "frequency", "Monthly")
    apply_annotations(txns, ann, rules)
    assert [t.frequency_detected for t in txns] == [False, True, True]
    assert {t.frequency for t in txns} == {"Monthly"}


def test_atm_withdrawal_and_cash_deposit_become_labelled_transfers():
    from src.core.transfer_detector import detect_cash_movements
    from src.models.transactions import TransactionStatus

    atm = Transaction(date(2026, 1, 5), "ATM WDL ATM CASH 1234", Decimal("500"), TransactionType.DEBIT, "SBI", "f")
    dep = Transaction(date(2026, 1, 6), "CASH DEPOSIT SELF AT X", Decimal("200"), TransactionType.CREDIT, "SBI", "f")
    pos = Transaction(date(2026, 1, 7), "POS ATM PURCH SHOP", Decimal("10"), TransactionType.DEBIT, "SBI", "f")
    detect_cash_movements([atm, dep, pos])
    assert (atm.status, atm.category) == (TransactionStatus.TRANSFER, "Cash/Withdrawal")
    assert (dep.status, dep.category) == (TransactionStatus.TRANSFER, "Cash/Deposit")
    assert (pos.status, pos.category) == (TransactionStatus.PENDING, None)
