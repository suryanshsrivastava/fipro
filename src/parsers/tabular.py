"""Shared implementation for bank statements that are a preamble followed by a header row and data rows."""

from abc import abstractmethod
from datetime import date
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
    A header ``signature`` is a set of lowercase column names; a row (or the dataframe's columns) is the
    header when at least three of a signature's names appear in it.
    """

    filename_marker: ClassVar[str]
    column_mapping: ClassVar[dict[str, list[str]]]
    detect_signatures: ClassVar[tuple[frozenset[str], ...]]
    # Defaults to ``detect_signatures``; HDFC also requires its "date" column to find the header row.
    header_signatures: ClassVar[tuple[frozenset[str], ...] | None] = None

    @staticmethod
    @abstractmethod
    def parse_date(date_str: str) -> date:
        """Parse the bank's date text; raises ValueError when it isn't a date."""

    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        if self.filename_marker not in filename.lower():
            return False
        tokens = {self.cell_text(v).lower() for v in df.head(_SCAN_ROWS).values.flatten() if self.cell_text(v)}
        tokens |= self._column_tokens(df)
        return self._matches(self.detect_signatures, tokens)

    def find_header_row(self, df: pd.DataFrame) -> int:
        """Row index of the header, or -1 when the dataframe's columns already are the header."""
        signatures = self.header_signatures or self.detect_signatures
        if self._matches(signatures, self._column_tokens(df)):
            return -1
        for idx in range(min(_SCAN_ROWS, len(df))):
            row_tokens = {self.cell_text(v).lower() for v in df.iloc[idx].tolist() if self.cell_text(v)}
            if self._matches(signatures, row_tokens):
                return idx
        raise ValueError(f"Header row not found for {self.bank_name} statement")

    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list[Transaction]:
        header_idx = self.find_header_row(df)
        if header_idx == -1:
            data = df.copy()
        else:
            data = df.iloc[header_idx + 1 :].copy()
            data.columns = df.iloc[header_idx].map(self.cell_text)
        data = data.dropna(how="all")

        columns = self._resolve_columns(data)
        transactions: list[Transaction] = []
        for _, row in data.iterrows():
            transaction = self._parse_row(row, columns, source_file)
            if transaction is not None:
                transactions.append(transaction)
        return transactions

    def _parse_row(self, row: pd.Series, columns: dict[str, str | None], source_file: str) -> Transaction | None:
        raw_date = self.cell_text(row.get(columns["transaction_date"], ""))
        if not raw_date:
            return None
        try:
            txn_date = self.parse_date(raw_date)
        except ValueError:
            return None

        description = self.cell_text(row.get(columns["description"], ""))
        if not description:
            return None

        debit_text = self._cell(row, columns["debit"])
        credit_text = self._cell(row, columns["credit"])
        amount_text = debit_text or credit_text
        if not amount_text:
            return None
        try:
            amount = parse_amount(amount_text)
        except ValueError:
            return None

        balance = None
        balance_text = self._cell(row, columns["balance"])
        if balance_text:
            try:
                balance = parse_amount(balance_text)
            except ValueError:
                balance = None

        return Transaction(
            transaction_date=txn_date,
            description=description,
            amount=amount,
            transaction_type=TransactionType.DEBIT if debit_text else TransactionType.CREDIT,
            source_bank=self.bank_name,
            source_file=source_file,
            balance=balance,
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

    def _column_tokens(self, df: pd.DataFrame) -> set[str]:
        return {self.cell_text(c).lower() for c in df.columns if self.cell_text(c)}

    @staticmethod
    def _matches(signatures: tuple[frozenset[str], ...], tokens: set[str]) -> bool:
        return any(len(signature & tokens) >= _MIN_SIGNATURE_MATCHES for signature in signatures)
