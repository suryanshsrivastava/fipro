import csv

import pytest

from src.core.annotations import overlay_labels, read_table, set_rule, write_table
from src.core.suggestions import confident_suggestions, suggest_categories

HASH = "0123456789abcdef"


def _setup(tmp_path):
    dash = tmp_path / "dashboard_data.csv"
    names = ["SWIGGY"] * 3 + ["UBER IND"] * 2 + ["MANDEEP SINGH", "JIO"]
    with open(dash, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["hash", "counterparty"])
        writer.writerows([[f"{i:016x}", n] for i, n in enumerate(names)])
    annotations, rules, suggestions = (str(tmp_path / n) for n in ("a.csv", "r.csv", "s.csv"))
    write_table(annotations, "hash", ("category",), {HASH: {"category": "City/Cab"}})
    write_table(rules, "counterparty", ("category",), {"jio": {"category": "Tech/Mobile Recharge"}})
    return str(dash), annotations, rules, suggestions


def test_suggest_scores_unruled_counterparties_once_most_frequent_first(tmp_path):
    dash, annotations, rules, suggestions = _setup(tmp_path)
    asked = []

    def fake(_endpoint, name, categories):
        asked.append((name, categories))
        return ("", 0.8) if name == "MANDEEP SINGH" else ("City/Cab", 0.99)

    assert suggest_categories("http://localhost:9931", dash, annotations, rules, suggestions, ask=fake) == 3
    # JIO has a rule (matched case-insensitively), so it is not scored; the model only chooses among used categories.
    assert [n for n, _ in asked] == ["SWIGGY", "UBER IND", "MANDEEP SINGH"]
    assert asked[0][1] == ["City/Cab", "Tech/Mobile Recharge"]
    assert read_table(suggestions, "counterparty")["MANDEEP SINGH"] == {
        "counterparty": "MANDEEP SINGH",
        "category": "",
        "probability": "0.80",
    }
    # Already-scored names are skipped on the next run, and "none of these" is never offered.
    assert suggest_categories("http://localhost:9931", dash, annotations, rules, suggestions, ask=fake) == 0
    assert set(confident_suggestions(suggestions)) == {"SWIGGY", "UBER IND"}


def test_suggest_refuses_a_remote_endpoint(tmp_path):
    dash, annotations, rules, suggestions = _setup(tmp_path)
    with pytest.raises(ValueError, match="this machine"):
        suggest_categories("https://api.example.com", dash, annotations, rules, suggestions, ask=lambda *_: ("x", 1.0))


def test_confident_suggestions_cut_off_at_ninety_percent(tmp_path):
    path = str(tmp_path / "s.csv")
    write_table(
        path,
        "counterparty",
        ("category", "probability"),
        {"A": {"category": "X", "probability": "0.90"}, "B": {"category": "X", "probability": "0.89"}},
    )
    assert set(confident_suggestions(path)) == {"A"}


def test_accepted_rule_shows_on_rows_without_their_own_category(tmp_path):
    rules, annotations = str(tmp_path / "r.csv"), str(tmp_path / "a.csv")
    write_table(annotations, "hash", ("category",), {HASH: {"category": "Mine"}})
    set_rule(rules, " swiggy ", "Entertainment/Eating out")
    rows = [
        {"hash": HASH, "counterparty": "SWIGGY", "category": ""},
        {"hash": "f" * 16, "counterparty": "SWIGGY", "category": ""},
        {"hash": "e" * 16, "counterparty": "UBER", "category": ""},
    ]
    overlay_labels(rows, annotations, rules)
    assert [r["category"] for r in rows] == ["Mine", "Entertainment/Eating out", ""]
    with pytest.raises(ValueError):
        set_rule(rules, "SWIGGY", "")


def test_bulk_category_labels_only_the_approved_hashes_and_rejects_bad_input(tmp_path):
    from src.core.annotations import set_category_many

    path = str(tmp_path / "a.csv")
    set_category_many(path, [HASH, "f" * 16], " City/Cab ")
    assert {h: r["category"] for h, r in read_table(path, "hash").items()} == {HASH: "City/Cab", "f" * 16: "City/Cab"}
    with pytest.raises(ValueError):
        set_category_many(path, [HASH, "nope"], "X")
    assert len(read_table(path, "hash")) == 2  # the failed call wrote nothing
