"""Helpers for raw export extraction fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.core.parser_registry import get_default_parser_registry

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def load_case_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_case_dataframe(case_dir: Path) -> pd.DataFrame:
    input_dir = case_dir / "input"
    registry = get_default_parser_registry()
    transactions = []
    for path in sorted(input_dir.iterdir()):
        if path.is_file():
            transactions.extend(registry.extract_transactions(str(path)).transactions)
    return pd.DataFrame.from_records(
        [
            {
                "transaction_date": t.transaction_date,
                "description": t.description,
                "amount": t.amount,
                "transaction_type": t.transaction_type.value,
                "source_bank": t.source_bank,
                "source_file": t.source_file,
                "balance": t.balance,
            }
            for t in transactions
        ]
    )


def extract_single_input_dataframe(case_dir: Path) -> pd.DataFrame:
    input_path = next(path for path in sorted(case_dir.iterdir()) if path.name.startswith("input."))
    parser = _parser_for_case(case_dir)
    dataframe = _load_case_dataframe(case_dir, input_path)
    transactions = parser.extract_transactions(dataframe, str(input_path))

    return pd.DataFrame.from_records(
        [
            {
                "transaction_date": transaction.transaction_date,
                "description": transaction.description,
                "amount": transaction.amount,
                "transaction_type": transaction.transaction_type.value,
                "source_bank": transaction.source_bank,
                "source_file": transaction.source_file,
                "balance": transaction.balance,
            }
            for transaction in transactions
        ]
    )


def normalize_dataframe(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []

    normalized = frame.copy()
    normalized["transaction_date"] = normalized["transaction_date"].map(lambda value: value.isoformat())
    normalized["amount"] = normalized["amount"].map(lambda value: f"{value:.2f}")
    normalized["transaction_type"] = normalized["transaction_type"].astype(str)
    normalized["source_bank"] = normalized["source_bank"].astype(str)
    normalized["source_file"] = normalized["source_file"].map(lambda value: Path(value).name)
    normalized["balance"] = normalized["balance"].map(_decimal_to_string)

    sort_columns = [
        "transaction_date",
        "source_bank",
        "source_file",
        "description",
        "amount",
        "transaction_type",
    ]
    normalized = normalized.sort_values(sort_columns, kind="stable").reset_index(drop=True)
    return normalized.to_dict(orient="records")


def _decimal_to_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return f"{value:.2f}"


def _parser_for_case(case_dir: Path):
    bank = case_dir.parent.name
    parser_registry = get_default_parser_registry()
    return parser_registry.parser_for_bank(bank)


def _load_case_dataframe(case_dir: Path, input_path: Path) -> pd.DataFrame:
    bank = case_dir.parent.name
    parser_registry = get_default_parser_registry()
    return parser_registry.load_dataframe(str(input_path), bank_hint=bank)
