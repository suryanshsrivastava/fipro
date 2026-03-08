"""Helpers for fixture-based parser regression tests."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pandas as pd

from src.models.transactions import Transaction
from src.parsers.axis import AxisParser
from src.parsers.hdfc import HDFCParser
from src.parsers.sbi import SBIParser


FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"


def load_case_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_transactions(transactions: list[Transaction]) -> list[dict[str, Any]]:
    normalized = []
    for transaction in transactions:
        normalized.append(
            {
                "transaction_date": transaction.transaction_date.isoformat(),
                "description": transaction.description,
                "amount": _decimal_to_string(transaction.amount),
                "transaction_type": transaction.transaction_type.value,
                "source_bank": transaction.source_bank,
                "balance": _decimal_to_string(transaction.balance),
            }
        )
    return normalized


def parse_hdfc_case(case_name: str) -> list[Transaction]:
    case_dir = FIXTURES_ROOT / "parsers" / "hdfc" / case_name
    parser = HDFCParser()
    dataframe = pd.read_excel(case_dir / "input.xlsx", engine="openpyxl", header=None)
    return parser.extract_transactions(dataframe, str(case_dir / "input.xlsx"))


def parse_sbi_case(case_name: str, extension: str) -> list[Transaction]:
    case_dir = FIXTURES_ROOT / "parsers" / "sbi" / case_name
    parser = SBIParser()
    input_path = case_dir / f"input.{extension}"
    dataframe = SBIParser.load_sbi_file(str(input_path))
    assert dataframe is not None
    return parser.extract_transactions(dataframe, str(input_path))


def parse_axis_case(case_name: str) -> list[Transaction]:
    case_dir = FIXTURES_ROOT / "parsers" / "axis" / case_name
    parser = AxisParser()
    dataframe = pd.read_excel(case_dir / "input.xlsx", engine="openpyxl", header=None)
    return parser.extract_transactions(dataframe, str(case_dir / "input.xlsx"))


def _decimal_to_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return f"{value:.2f}"
