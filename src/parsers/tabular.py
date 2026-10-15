"""Shared implementation for bank statements that are a preamble followed by a header row and data rows."""

from abc import abstractmethod
from datetime import date
from decimal import Decimal
from typing import ClassVar

import pandas as pd

from src.models.transactions import Transaction, TransactionType
from src.parsers.base import BankParser
from src.utils.amount_parser import parse_amount

_SCAN_ROWS = 25
_MIN_SIGNATURE_MATCHES = 3


class TabularStatementParser(BankParser):
    """
    A bank parser described by data: a filename marker, header signatures, column aliases and a date parser.

    Subclasses set the class attributes below; detection, header location and row extraction are shared.
    A ``signature`` is a set of lowercase column names; a row (or the dataframe's columns) is the
    header when at least three of a signature's names appear in it.
    """

    filename_marker: ClassVar[str]
    column_mapping: ClassVar[dict[str, list[str]]]
    detect_signatures: ClassVar[tuple[frozenset[str], ...]]

    @staticmethod
    @abstractmethod
    def parse_date(date_str: str) -> date:
        """Parse the bank's date text; raises ValueError when it isn't a date."""

    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        if self.filename_marker not in filename.lower():
            return False
        tokens = self._tokens(df.head(_SCAN_ROWS).values.flatten()) | self._tokens(df.columns)
        return self._matches(tokens)

    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list[Transaction]:
        data = self._with_header(df).dropna(how="all")
        columns = self._resolve_columns(data)
        transactions = (self._parse_row(row, columns, source_file) for _, row in data.iterrows())
        return [transaction for transaction in transactions if transaction is not None]

    def _with_header(self, df: pd.DataFrame) -> pd.DataFrame:
        """The data rows with the header applied; the frame is used as-is when its columns already are the header."""
        if self._matches(self._tokens(df.columns)):
            return df.copy()
        for idx in range(min(_SCAN_ROWS, len(df))):
            if self._matches(self._tokens(df.iloc[idx].tolist())):
                data = df.iloc[idx + 1 :].copy()
                data.columns = df.iloc[idx].map(self.cell_text)
                return data
        raise ValueError(f"Header row not found for {self.bank_name} statement")

    def _parse_row(self, row: pd.Series, columns: dict[str, str | None], source_file: str) -> Transaction | None:
        raw_date = self._cell(row, columns["transaction_date"])
        description = self._cell(row, columns["description"])
        if not raw_date or not description:
            return None
        try:
            txn_date = self.parse_date(raw_date)
        except ValueError:
            return None

        debit_text = self._cell(row, columns["debit"])
        credit_text = self._cell(row, columns["credit"])
        amount = _amount_or_none(debit_text or credit_text)
        if amount is None:
            return None

        return Transaction(
            transaction_date=txn_date,
            description=description,
            amount=amount,
            transaction_type=TransactionType.DEBIT if debit_text else TransactionType.CREDIT,
            source_bank=self.bank_name,
            source_file=source_file,
            balance=_amount_or_none(self._cell(row, columns["balance"])),
            raw_data=row.to_dict(),
        )

    def _cell(self, row: pd.Series, column: str | None) -> str:
        return self.cell_text(row.get(column, "")) if column else ""

    def _resolve_columns(self, data: pd.DataFrame) -> dict[str, str | None]:
        by_lower_name = {self.cell_text(c).lower(): c for c in data.columns if self.cell_text(c)}
        return {
            key: next((by_lower_name[a.lower()] for a in aliases if a.lower() in by_lower_name), None)
            for key, aliases in self.column_mapping.items()
        }

    def _tokens(self, values) -> set[str]:
        return {text.lower() for text in map(self.cell_text, values) if text}

    def _matches(self, tokens: set[str]) -> bool:
        return any(len(signature & tokens) >= _MIN_SIGNATURE_MATCHES for signature in self.detect_signatures)


def _amount_or_none(text: str) -> Decimal | None:
    """The parsed amount, or None when the text is empty or not an amount."""
    if not text:
        return None
    try:
        return parse_amount(text)
    except ValueError:
        return None
