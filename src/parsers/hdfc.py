"""
HDFC Bank statement parser.

This module implements the HDFCParser class for extracting transactions from
HDFC bank Excel statements. HDFC statements typically have:
- Header row around row 15-20 (after bank logo/address preamble)
- Date format: DD/MM/YY or DD-MM-YYYY
- Separate Withdrawal and Deposit columns
- Narration column for description
"""

from typing import List
import pandas as pd
from src.parsers.base import BankParser
from src.models.transactions import Transaction, TransactionType
from src.utils.date_parser import parse_hdfc_date
from src.utils.amount_parser import parse_amount


class HDFCParser(BankParser):
    """
    Parser for HDFC Bank Excel statements.
    
    Expected format:
    - File pattern: *hdfc*.xls, *hdfc*.xlsx
    - Header row: Usually row 15-20
    - Columns: Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance
    """
    
    @property
    def bank_name(self) -> str:
        """Return HDFC bank identifier."""
        return "HDFC"
    
    def can_parse(self, filename: str, df: pd.DataFrame) -> bool:
        """
        Check if file is an HDFC statement.
        
        Suggested implementation:
        - Check filename contains 'hdfc' (case-insensitive)
        - Check for HDFC-specific column names in first 20 rows
        """
        if "hdfc" not in filename.lower():
            return False

        head = df.head(20).fillna("")
        tokens = {str(v).strip().lower() for v in head.values.flatten()}
        expected = {"narration", "withdrawal amt.", "deposit amt."}
        # Require majority of expected columns to reduce false positives
        return len(expected.intersection(tokens)) >= 3
    
    def find_header_row(self, df: pd.DataFrame) -> int:
        """
        Find header row in HDFC statement.
        
        Suggested implementation:
        - Scan first 20 rows for expected column names
        - Look for: "Date", "Narration", "Withdrawal Amt.", "Deposit Amt."
        - Return row index where at least 3 expected columns are found
        """
        expected = {"date", "narration", "withdrawal amt.", "deposit amt."}
        for idx in range(min(20, len(df))):
            row_values = [str(v).strip().lower() for v in df.iloc[idx].tolist()]
            match_count = len(expected.intersection(row_values))
            if match_count >= 3:
                return idx
        raise ValueError("Header row not found for HDFC statement")
    
    def extract_transactions(self, df: pd.DataFrame, source_file: str) -> List[Transaction]:
        """
        Extract transactions from HDFC statement.
        
        Suggested implementation:
        - Use find_header_row to locate data start
        - Map columns: Date -> transaction_date, Narration -> description
        - Handle Withdrawal Amt. (debit) and Deposit Amt. (credit)
        - Parse dates in DD/MM/YY or DD-MM-YYYY format
        - Create Transaction objects with TransactionType.DEBIT or TransactionType.CREDIT
        """
        header_idx = self.find_header_row(df)
        headers = df.iloc[header_idx].fillna("").astype(str).str.strip()
        data = df.iloc[header_idx + 1 :].copy()
        data.columns = headers
        data = data.dropna(how="all")

        cols = self._resolve_columns(data)
        transactions: List[Transaction] = []

        for _, row in data.iterrows():
            raw_date = str(row.get(cols["transaction_date"], "")).strip()
            if not raw_date:
                continue
            try:
                txn_date = parse_hdfc_date(raw_date)
            except ValueError:
                continue

            description = str(row.get(cols["description"], "")).strip()
            if not description:
                continue

            debit_val = str(row.get(cols["debit"], "")).strip() if cols["debit"] else ""
            credit_val = str(row.get(cols["credit"], "")).strip() if cols["credit"] else ""

            amount_str = debit_val or credit_val
            if not amount_str:
                continue

            try:
                amount = parse_amount(amount_str)
            except ValueError:
                continue

            txn_type = TransactionType.DEBIT if debit_val else TransactionType.CREDIT

            balance = None
            if cols["balance"]:
                balance_raw = str(row.get(cols["balance"], "")).strip()
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
        Return HDFC column name mappings.
        
        Suggested return value:
        {
            "transaction_date": ["Date", "Value Dt"],
            "description": ["Narration"],
            "debit": ["Withdrawal Amt.", "Withdrawal"],
            "credit": ["Deposit Amt.", "Deposit"],
            "balance": ["Closing Balance"],
            "reference": ["Chq./Ref.No."]
        }
        """
        return {
            "transaction_date": ["Date", "Value Dt"],
            "description": ["Narration"],
            "debit": ["Withdrawal Amt.", "Withdrawal"],
            "credit": ["Deposit Amt.", "Deposit"],
            "balance": ["Closing Balance"],
            "reference": ["Chq./Ref.No."],
        }

    def _resolve_columns(self, df: pd.DataFrame) -> dict:
        mapping = self.get_column_mapping()
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

