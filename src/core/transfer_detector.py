"""
Internal transfer detection module for Fipro.

This module identifies transactions that represent money moving between the
user's own accounts (internal transfers). These should be flagged and optionally
excluded from budget calculations.
"""

from typing import List
from src.models.transactions import Transaction, TransactionStatus


def detect_transfers(transactions: List[Transaction]) -> List[Transaction]:
    """
    Detect and flag internal transfers.
    
    Identifies pairs of transactions that represent money moving between
    own accounts. Criteria:
    - Same date
    - Same amount (opposite signs)
    - Opposite transaction types (one debit, one credit)
    
    Args:
        transactions: List of Transaction objects
        
    Returns:
        List of Transaction objects with status updated for transfers
        
    Suggested implementation:
    - Sort transactions by date and amount
    - For each transaction:
      - Look for matching transaction on same date with opposite type and same amount
      - If found, set both status to TransactionStatus.TRANSFER
    - Return updated transactions list
    
    Functions that could be kept from existing code:
    - identify_internal_transfers() - identifies transfers in DataFrame
    """
    ordered_indices = sorted(
        range(len(transactions)),
        key=lambda idx: (
            transactions[idx].transaction_date,
            transactions[idx].amount,
            transactions[idx].source_bank,
        ),
    )
    matched: set[int] = set()

    for offset, idx in enumerate(ordered_indices):
        if idx in matched:
            continue

        for candidate_idx in ordered_indices[offset + 1 :]:
            if candidate_idx in matched:
                continue

            if is_transfer_pair(transactions[idx], transactions[candidate_idx]):
                transactions[idx].status = TransactionStatus.TRANSFER
                transactions[candidate_idx].status = TransactionStatus.TRANSFER
                matched.add(idx)
                matched.add(candidate_idx)
                break

    return transactions


def is_transfer_pair(txn1: Transaction, txn2: Transaction) -> bool:
    """
    Check if two transactions form an internal transfer pair.
    
    Args:
        txn1: First transaction
        txn2: Second transaction
        
    Returns:
        True if transactions form a transfer pair, False otherwise
        
    Suggested implementation:
    - Check same date
    - Check same absolute amount
    - Check opposite transaction types
    - Return True if all conditions met
    """
    return (
        txn1.transaction_date == txn2.transaction_date
        and txn1.amount == txn2.amount
        and txn1.transaction_type != txn2.transaction_type
        and txn1.source_bank != txn2.source_bank
    )
