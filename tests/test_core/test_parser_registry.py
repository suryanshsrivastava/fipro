from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from src.core.parser_registry import ParserAdapter, ParserRegistry
from src.models.transactions import Transaction, TransactionType
from src.parsers.base import BankParser
from src.parsers.sbi import SBIParser


class _DummyParser(BankParser):
    @property
    def bank_name(self) -> str:
        return "DUMMY"

    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        return filename.endswith(".dummy")

    def find_header_row(self, df: pd.DataFrame) -> int:
        return 0

    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list[Transaction]:
        return [
            Transaction(
                transaction_date=date(2026, 1, 1),
                description="demo",
                amount=Decimal("1.00"),
                transaction_type=TransactionType.CREDIT,
                source_bank=self.bank_name,
                source_file=source_file,
            )
        ]

    def get_column_mapping(self) -> dict:
        return {}


def test_infer_bank_from_filename_uses_registered_markers():
    registry = ParserRegistry()
    assert registry.infer_bank_from_filename("HDFC_may.xls") == "HDFC"
    assert registry.infer_bank_from_filename("sbi_statement.xlsx") == "SBI"
    assert registry.infer_bank_from_filename("axis_ledger.xls") == "AXIS"
    assert registry.infer_bank_from_filename("unknown_bank.xls") == "UNKNOWN"


def test_load_dataframe_uses_sbi_loader_for_sbi_files(monkeypatch: pytest.MonkeyPatch, tmp_path):
    expected = pd.DataFrame({"Txn Date": ["01 Jan 2026"], "Debit": ["100.00"], "Credit": [None], "Description": ["x"]})

    monkeypatch.setattr(SBIParser, "load_sbi_file", staticmethod(lambda _filepath: expected))
    registry = ParserRegistry()

    statement = tmp_path / "account_sbi.xls"
    statement.write_bytes(b"x")
    loaded = registry.load_dataframe(str(statement))
    assert loaded is expected


def test_extract_transactions_uses_single_registry_policy(tmp_path):
    parser = _DummyParser()
    adapter = ParserAdapter(
        parser=parser,
        filename_markers=("dummy",),
        loader=lambda _filepath: pd.DataFrame({"a": [1]}),
    )
    registry = ParserRegistry(adapters=[adapter])

    sample = tmp_path / "sample.dummy"
    sample.write_bytes(b"x")
    extracted = registry.extract_transactions(str(sample))
    assert extracted.parser.bank_name == "DUMMY"
    assert len(extracted.transactions) == 1
    assert extracted.transactions[0].source_file == str(sample)
