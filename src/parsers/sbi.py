"""
SBI Bank statement parser.

This module implements the SBIParser class for extracting transactions from
SBI bank statements. SBI statements can be:
- Tab-separated text files (often with .xls extension)
- Variable header row position (scan first 25 rows)
- Date format: DD MMM YYYY (e.g., "15 Nov 2025")
- Separate Debit and Credit columns
- Description column for transaction details
"""

import pandas as pd

from src.models.transactions import Transaction, TransactionType
from src.parsers.base import BankParser
from src.utils.amount_parser import parse_amount
from src.utils.date_parser import parse_sbi_date


class SBIParser(BankParser):
    """
    Parser for SBI Bank statements.

    Expected format:
    - File pattern: *sbi*.xls, *sbi*.xlsx
    - Format: Often tab-separated text despite .xls extension
    - Header row: Variable (scan first 25 rows)
    - Columns: Txn Date, Value Date, Description, Ref No./Cheque No., Debit, Credit, Balance
    """

    @property
    def bank_name(self) -> str:
        """Return SBI bank identifier."""
        return "SBI"

    @staticmethod
    def load_sbi_file(filepath: str) -> pd.DataFrame | None:
        """
        Load SBI statement file, handling both Excel and tab-separated formats.

        SBI often exports .xls files that are actually tab-separated text with
        metadata rows at the top. This method finds and loads from the header row.
        """
        # Try reading as tab-separated text first (common SBI format)
        try:
            # First, find the header row by scanning for "Txn Date"
            with open(filepath, encoding="utf-8") as f:
                lines = f.readlines()

            header_line_idx = None
            for idx, line in enumerate(lines):
                if "Txn Date" in line and "Debit" in line:
                    header_line_idx = idx
                    break

            if header_line_idx is not None:
                # Read from header row onwards
                df = pd.read_csv(filepath, sep="\t", encoding="utf-8", skiprows=header_line_idx, on_bad_lines="skip")
                if len(df.columns) > 3:
                    return df
        except Exception:
            pass

        # Try Excel formats
        for engine in ["xlrd", "openpyxl"]:
            try:
                df = pd.read_excel(filepath, engine=engine)
                return df
            except Exception:
                continue

        return None

    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        """
        Check if file is an SBI statement.

        Checks filename and looks for SBI-specific column names.
        """
        if "sbi" not in filename.lower():
            return False

        head = df.head(25)
        tokens = {self.cell_text(v).lower() for v in head.values.flatten() if self.cell_text(v)}
        # Also check column names
        col_tokens = {self.cell_text(c).lower() for c in df.columns if self.cell_text(c)}
        all_tokens = tokens.union(col_tokens)

        expected = {"txn date", "debit", "credit", "description"}
        return len(expected.intersection(all_tokens)) >= 3

    def find_header_row(self, df: pd.DataFrame) -> int:
        """
        Find header row in SBI statement.

        For tab-separated SBI files, the header is typically the first row
        with column names. Scans first 25 rows for expected column names.
        """
        expected = {"txn date", "description", "debit", "credit"}

        # First check if columns already contain expected headers
        col_values = [self.cell_text(c).lower() for c in df.columns if self.cell_text(c)]
        if len(expected.intersection(col_values)) >= 3:
            return -1  # Headers are already in columns, no header row in data

        # Scan rows for header
        for idx in range(min(25, len(df))):
            row_values = [self.cell_text(v).lower() for v in df.iloc[idx].tolist() if self.cell_text(v)]
            match_count = len(expected.intersection(row_values))
            if match_count >= 3:
                return idx
        raise ValueError("Header row not found for SBI statement")

    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> list[Transaction]:
        """
        Extract transactions from SBI statement.

        Handles both:
        - Tab-separated files where headers are already column names
        - Excel files where headers are in a data row
        """
        header_idx = self.find_header_row(df)

        if header_idx == -1:
            # Headers are already in df.columns (tab-separated format)
            data = df.copy()
        else:
            # Headers are in a data row (Excel format)
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
                txn_date = parse_sbi_date(raw_date)
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
        Return SBI column name mappings.

        Suggested return value:
        {
            "transaction_date": ["Txn Date", "Transaction Date", "Value Date"],
            "description": ["Description", "Particulars"],
            "debit": ["Debit"],
            "credit": ["Credit"],
            "balance": ["Balance"],
            "reference": ["Ref No./Cheque No.", "Ref No."]
        }
        """
        return {
            "transaction_date": ["Txn Date", "Transaction Date", "Value Date"],
            "description": ["Description", "Particulars"],
            "debit": ["Debit"],
            "credit": ["Credit"],
            "balance": ["Balance"],
            "reference": ["Ref No./Cheque No.", "Ref No."],
        }

    def _resolve_columns(self, df: pd.DataFrame, mapping: dict) -> dict:
        resolved: dict[str, str | None] = {}
        lower_cols = {self.cell_text(c).lower(): c for c in df.columns if self.cell_text(c)}
        for key, candidates in mapping.items():
            resolved[key] = None
            for candidate in candidates:
                cand_lower = candidate.lower()
                if cand_lower in lower_cols:
                    resolved[key] = lower_cols[cand_lower]
                    break
        return resolved
