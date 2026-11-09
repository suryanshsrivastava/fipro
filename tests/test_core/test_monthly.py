from datetime import date

from src.core.monthly import available_months, default_month, month_summary, previous_month


def _row(day, amount, bank="HDFC", category="", status="pending", **extra):
    return {
        "transaction_date": day,
        "amount": str(amount),
        "source_bank": bank,
        "category": category,
        "status": status,
        **extra,
    }


ROWS = [
    _row("2026-10-02", -100, category="Food", counterparty="SWIGGY", need_want="Want"),
    _row("2026-10-03", -50, bank="UNI_VISA", category="Food", counterparty="SWIGGY"),
    _row("2026-10-04", 20, bank="UNI_VISA", category="Food", counterparty="SWIGGY"),  # card refund
    _row("2026-10-05", 1000, bank="AXIS", description="SALARY"),  # income
    _row("2026-10-06", -300, status="internal_transfer"),  # card bill payment: not spend
    _row("2026-10-07", -40, frequency="Monthly", counterparty="NETFLIX"),
    _row("2026-09-02", -500, category="Food"),
]


def test_summary_counts_refunds_against_spend_and_ignores_transfers():
    s = month_summary(ROWS, "2026-10")
    assert (s["income"], s["spend"], s["refunds"], s["net_spend"], s["saved"]) == (1000, 190, 20, 170, 830)
    assert s["transfers"] == {"count": 1, "amount": 300}
    assert s["recurring"] == 40
    assert s["uncategorised"] == {"count": 1, "amount": 40}


def test_categories_are_net_of_refunds_and_carry_last_months_figure():
    food = next(c for c in month_summary(ROWS, "2026-10")["by_category"] if c["name"] == "Food")
    assert (food["amount"], food["previous"]) == (130, 500)


def test_payees_accounts_and_labels():
    s = month_summary(ROWS, "2026-10")
    assert s["top_payees"][0] == {"name": "SWIGGY", "amount": 130, "previous": 0.0}
    assert {a["name"]: a["amount"] for a in s["by_account"]} == {"HDFC": 140, "UNI_VISA": 30}
    assert s["need_want"] == {"Want": 100, "Unlabelled": 70}
    assert s["previous"] == {"income": 0, "net_spend": 500}


def test_month_helpers():
    assert available_months(ROWS) == ["2026-10", "2026-09"]
    assert previous_month("2026-01") == "2025-12"
    assert default_month(["2026-11", "2026-10"], date(2026, 11, 8)) == "2026-10"  # November is still in progress
    assert default_month(["2026-11"], date(2026, 11, 8)) == "2026-11"
    assert default_month([], date(2026, 11, 8)) is None
