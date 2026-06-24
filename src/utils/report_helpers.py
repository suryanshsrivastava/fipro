"""Shared helpers for processing reports and hub summaries."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.transactions import Transaction


_TOP_DESCRIPTION_LIMIT = 15
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_description_key(description: str) -> str:
    """Collapse whitespace for grouping similar narration lines."""
    s = description.strip()
    if not s:
        return ""
    return _WHITESPACE_RE.sub(" ", s)


def include_internal_transfers_from_config(config: dict | None) -> bool:
    """Resolve export/report transfer inclusion from processing config."""
    if config is None:
        return True
    processing = config.get("processing", {})
    if "include_internal_transfers" in processing:
        return bool(processing["include_internal_transfers"])
    return not processing.get("skip_internal_transfers", False)


def filter_transactions_for_export(
    transactions: list[Transaction],
    include_internal_transfers: bool,
) -> list[Transaction]:
    """Match Goodbudget export: optionally drop internal transfers."""
    from src.models.transactions import TransactionStatus

    if include_internal_transfers:
        return list(transactions)
    return [t for t in transactions if t.status != TransactionStatus.TRANSFER]


def cash_flow_from_transactions(transactions: Iterable[Transaction]) -> dict:
    """Total credits, debits, and net (signed) from transaction rows."""
    from src.models.transactions import TransactionType

    total_credits = Decimal("0")
    total_debits = Decimal("0")
    for t in transactions:
        if t.transaction_type == TransactionType.CREDIT:
            total_credits += abs(t.amount)
        else:
            total_debits += abs(t.amount)
    net = total_credits - total_debits
    return {
        "total_credits": str(total_credits),
        "total_debits": str(total_debits),
        "net_cash_flow": str(net),
    }


def top_descriptions(
    transactions: Iterable[Transaction],
    *,
    limit: int = _TOP_DESCRIPTION_LIMIT,
) -> list[dict[str, str | int]]:
    """Most frequent normalized descriptions with counts."""
    counts: Counter[str] = Counter()
    for t in transactions:
        key = normalize_description_key(t.description)
        if key:
            counts[key] += 1
    out: list[dict[str, str | int]] = []
    for desc, cnt in counts.most_common(limit):
        out.append({"description": desc, "count": cnt})
    return out


def ending_balances_by_statement(transactions: list[Transaction]) -> dict:
    """
    Per-(bank, source_file) closing balance from the latest dated row with balance.

    total_across_statements is set only when every such group has a closing balance;
    otherwise total_across_statements is null and reason explains why.
    """
    groups: dict[tuple[str, str], list[Transaction]] = {}
    for t in transactions:
        groups.setdefault((t.source_bank, t.source_file), []).append(t)

    by_statement: list[dict] = []
    missing_balance_files: list[str] = []

    for (bank, source_file), rows in sorted(groups.items()):
        with_balance = [t for t in rows if t.balance is not None]
        if not with_balance:
            missing_balance_files.append(Path(source_file).name)
            by_statement.append(
                {
                    "bank": bank,
                    "source_file": Path(source_file).name,
                    "closing_balance": None,
                    "as_of_date": None,
                }
            )
            continue
        row_order = {id(t): i for i, t in enumerate(rows)}
        latest = max(
            with_balance,
            key=lambda t: (t.transaction_date, row_order.get(id(t), 0)),
        )
        by_statement.append(
            {
                "bank": bank,
                "source_file": Path(source_file).name,
                "closing_balance": str(latest.balance),
                "as_of_date": latest.transaction_date.isoformat(),
            }
        )

    total: Decimal | None
    reason: str | None
    if not transactions:
        total = None
        reason = "no_transactions"
    elif missing_balance_files:
        total = None
        reason = "missing_balance_on_one_or_more_statements_not_a_full_net_worth_view"
    else:
        total = sum(
            (Decimal(item["closing_balance"]) for item in by_statement),
            Decimal("0"),
        )
        reason = None

    return {
        "by_statement": by_statement,
        "total_across_statements": str(total) if total is not None else None,
        "reason_if_no_total": reason,
    }
