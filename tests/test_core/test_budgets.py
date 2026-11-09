from src.core.budgets import load_budgets, seed_budgets, set_budget


def _spend(month: str, category: str, amount: float) -> dict:
    return {"transaction_date": f"{month}-05", "amount": str(-amount), "category": category, "source_bank": "HDFC"}


def test_a_target_can_be_set_changed_and_removed(tmp_path):
    path = str(tmp_path / "budgets.csv")
    set_budget(path, "Food/Groceries", 8000)
    set_budget(path, "Food/Groceries", 9000)
    set_budget(path, "City/Cab", 2000)
    set_budget(path, "City/Cab", 0)
    assert load_budgets(path) == {"Food/Groceries": 9000.0}


def test_seeding_averages_the_three_months_before_and_keeps_existing_targets(tmp_path):
    path = str(tmp_path / "budgets.csv")
    rows = [_spend(m, "Food/Groceries", a) for m, a in (("2026-07", 3000), ("2026-08", 6000), ("2026-09", 7000))]
    rows += [_spend("2026-09", "City/Cab", 40), _spend("2026-09", "", 9999), _spend("2026-10", "Food/Groceries", 99999)]
    set_budget(path, "House/Rent", 20000)
    assert seed_budgets(path, rows, "2026-10") == 1  # cab rounds to 0 and Uncategorised is skipped
    assert load_budgets(path) == {"Food/Groceries": 5300.0, "House/Rent": 20000.0}
