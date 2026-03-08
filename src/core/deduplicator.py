"""
Transaction deduplication module for Fipro.

This module handles hash-based deduplication of transactions to prevent
duplicate entries when processing the same file multiple times or when
transactions appear in multiple statements.
"""

from typing import List, Set, Tuple
from src.models.transactions import Transaction


def deduplicate(transactions: List[Transaction], seen_hashes: Set[str] = None) -> Tuple[List[Transaction], int]:
    """
    Remove duplicate transactions based on hash.
    
    Uses the transaction hash generated in Transaction.__post_init__ to
    identify duplicates. For MVP, uses in-memory set of seen hashes.
    
    Args:
        transactions: List of Transaction objects to deduplicate
        seen_hashes: Set of previously seen transaction hashes (optional)
        
    Returns:
        Tuple of (deduplicated_transactions, duplicates_skipped_count)
        
    Suggested implementation:
    - Initialize seen_hashes set if None
    - For each transaction:
      - Check if transaction.hash in seen_hashes
      - If not seen, add to result list and add hash to seen_hashes
      - If seen, increment duplicate counter
    - Return (deduplicated_list, duplicate_count)
    
    Functions that could be kept from existing code:
    - deduplicate_transactions() - removes duplicates from DataFrame
    """
    if seen_hashes is None:
        seen_hashes = set()

    deduplicated: List[Transaction] = []
    duplicates_skipped = 0

    for transaction in transactions:
        if transaction.hash in seen_hashes:
            duplicates_skipped += 1
            continue
        seen_hashes.add(transaction.hash)
        deduplicated.append(transaction)

    return deduplicated, duplicates_skipped


def get_seen_hashes_from_file(filepath: str) -> Set[str]:
    """
    Load previously seen transaction hashes from file.
    
    For future use when implementing persistent deduplication (v1.2).
    Currently returns empty set for MVP.
    
    Args:
        filepath: Path to hash storage file
        
    Returns:
        Set of transaction hashes
    """
    return set()


def save_seen_hashes_to_file(hashes: Set[str], filepath: str) -> None:
    """
    Save transaction hashes to file for persistent deduplication.
    
    For future use when implementing persistent deduplication (v1.2).
    Currently no-op for MVP.
    
    Args:
        hashes: Set of transaction hashes to save
        filepath: Path to hash storage file
    """
    return None
