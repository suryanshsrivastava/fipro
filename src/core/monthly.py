"""Month-by-month analysis of the exported transactions: the numbers behind the Monthly screen.

Counting rules, which a budget will reuse:

* Internal transfers (bank to bank, card bill payments, cash, settlements) are neither spend nor income.
* Credits on a bank account are income; credits on a card (refunds, cashback) reduce spend.
* Spend is shown net of those refunds, in total and per category.
"""

from collections import defaultdict
from datetime import date

from src.utils.narration import CARD_BANKS

UNCATEGORISED = "Uncategorised"
_TRANSFER = "internal_transfer"


def available_months(rows: list[dict]) -> list[str]:
    """Months (``YYYY-MM``) that have any transaction, newest first."""
    return sorted({r["transaction_date"][:7] for r in rows if r.get("transaction_date")}, reverse=True)


def default_month(months: list[str], today: date) -> str | None:
    """The latest finished month, else the latest month there is: a month in progress is a poor default."""
    finished = [m for m in months if m < today.strftime("%Y-%m")]
    return (finished or months)[0] if months else None


def previous_month(month: str) -> str:
    year, number = int(month[:4]), int(month[5:7])
    return f"{year - 1}-12" if number == 1 else f"{year}-{number - 1:02d}"


def month_summary(rows: list[dict], month: str) -> dict:
    """Income, spend, and the spend broken down by category, payee, account, day and label, for one month."""
    current = _totals(rows, month)
    earlier = _totals(rows, previous_month(month))
    return {
        "month": month,
        "previous_month": previous_month(month),
        "income": current["income"],
        "spend": current["spend"],
        "refunds": current["refunds"],
        "net_spend": current["spend"] - current["refunds"],
        "saved": current["income"] - (current["spend"] - current["refunds"]),
        "previous": {
            "income": earlier["income"],
            "net_spend": earlier["spend"] - earlier["refunds"],
        },
        "by_category": _ranked(current["category"], earlier["category"]),
        "top_payees": _ranked(current["payee"], {})[:10],
        "by_account": _ranked(current["account"], earlier["account"]),
        "by_day": [{"day": d, "amount": a} for d, a in sorted(current["day"].items())],
        "need_want": dict(current["need_want"]),
        "recurring": current["recurring"],
        "uncategorised": {
            "count": current["uncategorised_count"],
            "amount": current["category"].get(UNCATEGORISED, 0.0),
        },
        "transactions": current["count"],
        "transfers": {"count": current["transfer_count"], "amount": current["transfer_amount"]},
    }


def _totals(rows: list[dict], month: str) -> dict:
    out: dict = {
        "income": 0.0,
        "spend": 0.0,
        "refunds": 0.0,
        "recurring": 0.0,
        "count": 0,
        "uncategorised_count": 0,
        "transfer_count": 0,
        "transfer_amount": 0.0,
        "category": defaultdict(float),
        "payee": defaultdict(float),
        "account": defaultdict(float),
        "day": defaultdict(float),
        "need_want": defaultdict(float),
    }
    for row in rows:
        if not row.get("transaction_date", "").startswith(month):
            continue
        amount = _amount(row)
        out["count"] += 1
        if row.get("status") == _TRANSFER:
            out["transfer_count"] += 1
            out["transfer_amount"] += abs(amount)
            continue
        is_card = row.get("source_bank") in CARD_BANKS
        if amount > 0 and not is_card:
            out["income"] += amount
            continue
        # A debit adds to spend; a card credit (refund, cashback) takes the same amount off.
        spent = -amount
        category = row.get("category") or UNCATEGORISED
        if amount < 0:
            out["spend"] += spent
            if category == UNCATEGORISED:
                out["uncategorised_count"] += 1
            if row.get("frequency") == "Monthly":
                out["recurring"] += spent
        else:
            out["refunds"] += amount
        out["category"][category] += spent
        out["payee"][row.get("counterparty") or _shorten(row.get("description", ""))] += spent
        out["account"][row.get("source_bank", "")] += spent
        out["day"][row["transaction_date"]] += spent
        out["need_want"][row.get("need_want") or "Unlabelled"] += spent
    return out


def _ranked(current: dict[str, float], earlier: dict[str, float]) -> list[dict]:
    """Items by amount, largest first, each with last month's amount; zero or negative net items are dropped."""
    return [
        {"name": name, "amount": amount, "previous": earlier.get(name, 0.0)}
        for name, amount in sorted(current.items(), key=lambda item: -item[1])
        if amount > 0
    ]


def _amount(row: dict) -> float:
    try:
        return float(row.get("amount") or 0)
    except ValueError:
        return 0.0


def _shorten(description: str) -> str:
    return " ".join(description.split())[:28] or "(no payee)"
