"""
SBI Bank statement parser.

This module implements the SBIParser class for extracting transactions from
SBI bank Excel statements. SBI statements typically have:
- Variable header row position (scan first 20 rows)
- Date format: DD MMM YYYY (e.g., "15 Nov 2025")
- Separate Debit and Credit columns
- Description or Particulars column
"""

from typing import List
import pandas as pd
from src.parsers.base import BankParser
from src.models.transactions import Transaction, TransactionType
from src.utils.date_parser import parse_sbi_date
from src.utils.amount_parser import parse_amount


class SBIParser(BankParser):
    """
    Parser for SBI Bank Excel statements.
    
    Expected format:
    - File pattern: *sbi*.xls, *sbi*.xlsx
    - Header row: Variable (scan first 20 rows)
    - Columns: Txn Date, Value Date, Description, Ref No./Cheque No., Debit, Credit, Balance
    """
    
    @property
    def bank_name(self) -> str:
        """Return SBI bank identifier."""
        return "SBI"
    
    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        """
        Check if file is an SBI statement.
        
        Suggested implementation:
        - Check filename contains 'sbi' (case-insensitive)
        - Check for SBI-specific column names in first 20 rows
        """
        if "sbi" not in filename.lower():
            return False

        head = df.head(20).fillna("")
        tokens = {str(v).strip().lower() for v in head.values.flatten()}
        expected = {"txn date", "debit", "credit"}
        return len(expected.intersection(tokens)) >= 3
    
    def find_header_row(self, df: pd.DataFrame) -> int:
        """
        Find header row in SBI statement.
        
        Suggested implementation:
        - Scan first 20 rows for expected column names
        - Look for: "Txn Date", "Description", "Debit", "Credit"
        - Return row index where at least 3 expected columns are found
        """
        expected = {"txn date", "description", "debit", "credit"}
        for idx in range(min(20, len(df))):
            row_values = [str(v).strip().lower() for v in df.iloc[idx].tolist()]
            match_count = len(expected.intersection(row_values))
            if match_count >= 3:
                return idx
        raise ValueError("Header row not found for SBI statement")
    
    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> List[Transaction]:
        """
        Extract transactions from SBI statement.
        
        Suggested implementation:
        - Use find_header_row to locate data start
        - Map columns: Txn Date -> transaction_date, Description -> description
        - Handle Debit and Credit columns
        - Parse dates in DD MMM YYYY format (e.g., "15 Nov 2025")
        - Create Transaction objects with TransactionType.DEBIT or TransactionType.CREDIT
        """
        header_idx = self.find_header_row(df)
        headers = df.iloc[header_idx].fillna("").astype(str).str.strip()
        data = df.iloc[header_idx + 1 :].copy()
        data.columns = headers
        data = data.dropna(how="all")

        cols = self.get_column_mapping()
        resolved = self._resolve_columns(data, cols)

        transactions: List[Transaction] = []

        for _, row in data.iterrows():
            raw_date = str(row.get(resolved["transaction_date"], "")).strip()
            if not raw_date:
                continue
            try:
                txn_date = parse_sbi_date(raw_date)
            except ValueError:
                continue

            description = str(row.get(resolved["description"], "")).strip()
            if not description:
                continue

            debit_val = str(row.get(resolved["debit"], "")).strip() if resolved["debit"] else ""
            credit_val = str(row.get(resolved["credit"], "")).strip() if resolved["credit"] else ""

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
                balance_raw = str(row.get(resolved["balance"], "")).strip()
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
        resolved = {}
        lower_cols = {str(c).strip().lower(): c for c in df.columns}
        for key, candidates in mapping.items():
            resolved[key] = None
            for candidate in candidates:
                cand_lower = candidate.lower()
                if cand_lower in lower_cols:
                    resolved[key] = lower_cols[cand_lower]
                    break
        return resolved

