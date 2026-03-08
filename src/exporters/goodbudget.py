"""
Goodbudget CSV exporter for Fipro.

This module handles exporting transactions to Goodbudget-compatible CSV format.
Goodbudget is an envelope budgeting app that accepts CSV imports with specific
column requirements.
"""

from typing import List
from pathlib import Path
from src.models.transactions import Transaction


def export_to_goodbudget(transactions: List[Transaction], output_path: str, config: dict) -> None:
    """
    Export transactions to Goodbudget CSV format.
    
    Generates a CSV file with columns:
    Date, Envelope, Account, Name, Notes, Amount, Status
    
    Args:
        transactions: List of Transaction objects to export
        output_path: Path to output CSV file
        config: Configuration dictionary with export settings
        
    Suggested implementation:
    - Filter out internal transfers if config['processing']['skip_internal_transfers'] is True
    - Sort transactions by date
    - For each transaction, call transaction.to_goodbudget_row()
    - Write CSV with UTF-8 encoding
    - Include header row: Date,Envelope,Account,Name,Notes,Amount,Status
    """
    pass


def format_goodbudget_row(transaction: Transaction, config: dict) -> dict:
    """
    Format a single transaction for Goodbudget CSV.
    
    Args:
        transaction: Transaction object to format
        config: Configuration with export settings
        
    Returns:
        Dictionary with Goodbudget CSV columns
        
    Note:
        Transaction.to_goodbudget_row() already implements this,
        but this function can apply additional config-based formatting.
    """
    pass

