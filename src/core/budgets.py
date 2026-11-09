"""Monthly spending targets per category, kept in ``corpus/state/budgets.csv`` (``category, amount``).

A target applies to every month. Setting an amount of 0 or less removes it. ``seed_budgets`` proposes targets from
what was actually spent, and never overwrites one you set.
"""

from src.core.annotations import read_table, write_table
from src.core.monthly import UNCATEGORISED, month_summary, previous_month

BUDGET_FIELDS = ("amount",)
_ROUND_TO = 100
_SEED_MONTHS = 3


def load_budgets(path: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for category, row in read_table(path, "category").items():
        try:
            amount = float(row.get("amount") or 0)
        except ValueError:
            continue
        if amount > 0:
            out[category] = amount
    return out


def set_budget(path: str, category: str, amount: float) -> None:
    category = category.strip()
    if not category or category == UNCATEGORISED:
        raise ValueError("a target needs a real category")
    rows = read_table(path, "category")
    if amount > 0:
        rows[category] = {"amount": f"{amount:.0f}"}
    else:
        rows.pop(category, None)
    write_table(path, "category", BUDGET_FIELDS, rows)


def seed_budgets(path: str, rows: list[dict], month: str) -> int:
    """Give each category without a target the average of its spend in the three months before ``month``."""
    totals: dict[str, float] = {}
    earlier = month
    for _ in range(_SEED_MONTHS):
        earlier = previous_month(earlier)
        for item in month_summary(rows, earlier)["by_category"]:
            totals[item["name"]] = totals.get(item["name"], 0.0) + item["amount"]
    table = read_table(path, "category")
    added = 0
    for category, total in totals.items():
        target = round(total / _SEED_MONTHS / _ROUND_TO) * _ROUND_TO
        if category != UNCATEGORISED and category not in table and target > 0:
            table[category] = {"amount": str(target)}
            added += 1
    if added:
        write_table(path, "category", BUDGET_FIELDS, table)
    return added
