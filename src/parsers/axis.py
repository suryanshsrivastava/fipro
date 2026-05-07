"""
Axis Bank statement parser.

This module implements the AxisParser class for extracting transactions from
Axis bank Excel statements. Axis statements typically have:
- Header row around row 10-15
- Date format: DD-MM-YYYY
- Separate Debit and Credit columns
- Particulars column for description
"""

import pandas as pd

from src.models.transactions import Transaction, TransactionType
from src.parsers.base import BankParser
from src.utils.amount_parser import parse_amount
from src.utils.date_parser import parse_axis_date


class AxisParser(BankParser):
    """
    Parser for Axis Bank Excel statements.

    Expected format:
    - File pattern: *axis*.xls, *axis*.xlsx
    - Header row: Usually row 10-15
    - Columns: Tran Date, Particulars, Chq No, Debit, Credit, Balance
    """

    @property
    def bank_name(self) -> str:
        """Return AXIS bank identifier."""
        return "AXIS"

    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        """
        Check if file is an Axis statement.

        Checks filename and looks for Axis-specific column names.
        Axis uses abbreviated column names: DR, CR, BAL, PARTICULARS
        """
        if "axis" not in filename.lower():
            return False

        head = df.head(25)
        tokens = {self.cell_text(v).lower() for v in head.values.flatten() if self.cell_text(v)}
        # Axis uses abbreviated column names
        expected_full = {"tran date", "particulars", "debit", "credit"}
        expected_abbrev = {"tran date", "particulars", "dr", "cr"}

        match_full = len(expected_full.intersection(tokens))
        match_abbrev = len(expected_abbrev.intersection(tokens))

        return match_full >= 3 or match_abbrev >= 3

    def find_header_row(self, df: pd.DataFrame) -> int:
        """
        Find header row in Axis statement.

        Scans first 20 rows for expected column names.
        Handles both full names (Debit, Credit) and abbreviations (DR, CR).
        """
        expected_full = {"tran date", "particulars", "debit", "credit"}
        expected_abbrev = {"tran date", "particulars", "dr", "cr"}
        
        for idx in range(min(25, len(df))):
            row_values = [self.cell_text(v).lower() for v in df.iloc[idx].tolist() if self.cell_text(v)]
            match_full = len(expected_full.intersection(row_values))
            match_abbrev = len(expected_abbrev.intersection(row_values))
            if match_full >= 3 or match_abbrev >= 3:
                return idx
        raise ValueError("Header row not found for Axis statement")

    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list[Transaction]:
        """
        Extract transactions from Axis statement.

        Suggested implementation:
        - Use find_header_row to locate data start
        - Map columns: Tran Date -> transaction_date, Particulars -> description
        - Handle Debit and Credit columns
        - Parse dates in DD-MM-YYYY format
        - Create Transaction objects with TransactionType.DEBIT or TransactionType.CREDIT
        """
        header_idx = self.find_header_row(df)
        headers = df.iloc[header_idx].map(self.cell_text)
        data = df.iloc[header_idx + 1 :].copy()
        data.columns = headers
        data = data.dropna(how="all")

        cols = self.get_column_mapping()
        resolved = self._resolve_columns(data, cols)

        transactions: list[Transaction] = []

        for _, row in data.iterrows():
            raw_date = self.cell_text(row.get(resolved["transaction_date"], ""))
            if not raw_date:
                continue
            try:
                txn_date = parse_axis_date(raw_date)
            except ValueError:
                continue

            description = self.cell_text(row.get(resolved["description"], ""))
            if not description:
                continue

            debit_val = self.cell_text(row.get(resolved["debit"], "")) if resolved["debit"] else ""
            credit_val = self.cell_text(row.get(resolved["credit"], "")) if resolved["credit"] else ""

            amount_str = debit_val or credit_val
            if not amount_str:
                continue

            try:
                amount = parse_amount(amount_str)
            except ValueError:
                continue

            txn_type = TransactionType.DEBIT if debit_val else TransactionType.CREDIT

            balance = None
            if resolved["balance"]:
                balance_raw = self.cell_text(row.get(resolved["balance"], ""))
                if balance_raw:
                    try:
                        balance = parse_amount(balance_raw)
                    except ValueError:
                        balance = None

            transactions.append(
                Transaction(
                    transaction_date=txn_date,
                    description=description,
                    amount=amount,
                    transaction_type=txn_type,
                    source_bank=self.bank_name,
                    source_file=source_file,
                    balance=balance,
                    raw_data=row.to_dict(),
                )
            )

        return transactions

    def get_column_mapping(self) -> dict:
        """
        Return Axis column name mappings.

        Includes both full names and abbreviations used by Axis.
        """
        return {
            "transaction_date": ["Tran Date", "Transaction Date"],
            "description": ["Particulars", "PARTICULARS"],
            "debit": ["Debit", "DR"],
            "credit": ["Credit", "CR"],
            "balance": ["Balance", "BAL"],
            "reference": ["Chq No", "Cheque No.", "CHQNO"],
        }

    def _resolve_columns(self, df: pd.DataFrame, mapping: dict) -> dict:
        resolved = {}
        lower_cols = {
            self.cell_text(c).lower(): c
            for c in df.columns
            if self.cell_text(c)
        }
        for key, candidates in mapping.items():
            resolved[key] = None
            for candidate in candidates:
                cand_lower = candidate.lower()
                if cand_lower in lower_cols:
                    resolved[key] = lower_cols[cand_lower]
                    break
        return resolved
