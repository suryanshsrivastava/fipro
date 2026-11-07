"""Category suggestions from a local decision model.

``fipro suggest`` asks a llama.cpp server (``/v1/systemone``) which of your own categories each counterparty
belongs to, using the counterparty name only: no amounts, dates or account numbers. The endpoint must be on
this machine, so nothing leaves it. Answers go to ``suggestions.csv``; the dashboard offers the confident ones
and only a click turns one into a rule in ``category_rules.csv``.
"""

import csv
import json
import urllib.request
from collections import Counter
from collections.abc import Callable
from urllib.parse import urlparse

from src.core.annotations import read_table, write_table

SUGGESTION_FIELDS = ("category", "probability")
# Answer for payees the categories cannot describe (people, wallets, anything new); stored as an empty category.
NONE_OF_THESE = "None of these"
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}
_SAVE_EVERY = 25


def known_categories(annotations_path: str, rules_path: str) -> list[str]:
    """The categories you have used so far: the model chooses among these and never invents one."""
    used = {row.get("category", "").strip() for row in read_table(annotations_path, "hash").values()}
    used |= {row.get("category", "").strip() for row in read_table(rules_path, "counterparty").values()}
    return sorted(used - {""})


def ask_model(endpoint: str, counterparty: str, categories: list[str]) -> tuple[str, float]:
    """Best category for one counterparty and its probability (``""`` when none of the categories fit)."""
    criteria: dict[str, str | None] = dict.fromkeys(categories)
    criteria[NONE_OF_THESE] = "a person, a wallet or payment app, or anything not covered by the other options"
    request = {
        "state": f"Counterparty of a payment from an Indian bank account: {counterparty}",
        "questions": {
            "category": {
                "type": "choice",
                "instructions": "Which spending category does this counterparty belong to?",
                "criteria": criteria,
            }
        },
    }
    http = urllib.request.Request(
        f"{endpoint.rstrip('/')}/v1/systemone", json.dumps(request).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(http, timeout=120) as response:
        answer = json.load(response)["answers"]["category"]
    choice = answer["choice"]
    return ("" if choice == NONE_OF_THESE else choice), float(answer["probabilities"][choice])


def counterparties_to_score(dashboard_csv: str, rules_path: str, scored: set[str]) -> list[str]:
    """Counterparties with no rule and no suggestion yet, most frequent first."""
    with open(dashboard_csv, newline="") as f:
        counts = Counter(row["counterparty"] for row in csv.DictReader(f) if row.get("counterparty"))
    ruled = {name.upper() for name in read_table(rules_path, "counterparty")}
    return [name for name, _ in counts.most_common() if name.upper() not in ruled and name not in scored]


def suggest_categories(
    endpoint: str,
    dashboard_csv: str,
    annotations_path: str,
    rules_path: str,
    suggestions_path: str,
    limit: int | None = None,
    ask: Callable[[str, str, list[str]], tuple[str, float]] = ask_model,
) -> int:
    """Score unscored counterparties (at most ``limit``) and save after every few; returns how many were scored."""
    if urlparse(endpoint).hostname not in _LOOPBACK:
        raise ValueError(f"the model endpoint must be on this machine (localhost), not {endpoint!r}")
    categories = known_categories(annotations_path, rules_path)
    if not categories:
        raise ValueError("no categories yet: label some transactions first")
    suggestions = read_table(suggestions_path, "counterparty")
    todo = counterparties_to_score(dashboard_csv, rules_path, set(suggestions))[:limit]
    for done, name in enumerate(todo, 1):
        category, probability = ask(endpoint, name, categories)
        suggestions[name] = {"category": category, "probability": f"{probability:.2f}"}
        if done % _SAVE_EVERY == 0 or done == len(todo):
            write_table(suggestions_path, "counterparty", SUGGESTION_FIELDS, suggestions)
    return len(todo)


def confident_suggestions(suggestions_path: str, minimum: float = 0.9) -> dict[str, dict[str, object]]:
    """Suggestions the dashboard offers: a real category at or above ``minimum`` probability."""
    return {
        name: {"category": row["category"], "probability": float(row["probability"])}
        for name, row in read_table(suggestions_path, "counterparty").items()
        if row.get("category") and float(row.get("probability") or 0) >= minimum
    }
