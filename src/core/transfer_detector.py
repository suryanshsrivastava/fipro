from collections import defaultdict

from src.models.transactions import Transaction, TransactionStatus, TransactionType


def detect_transfers(transactions: list[Transaction]) -> list[Transaction]:
    grouped: dict[tuple, list[Transaction]] = defaultdict(list)
    for txn in transactions:
        if txn.status == TransactionStatus.TRANSFER:
            continue
        grouped[(txn.transaction_date, txn.amount)].append(txn)

    for candidates in grouped.values():
        debits = [t for t in candidates if t.transaction_type == TransactionType.DEBIT]
        credits = [t for t in candidates if t.transaction_type == TransactionType.CREDIT]
        used_credits: set[int] = set()

        for debit in debits:
            for index, credit in enumerate(credits):
                if index in used_credits:
                    continue
                if not is_transfer_pair(debit, credit):
                    continue
                mark_transfer_pair(debit, credit)
                used_credits.add(index)
                break
    return transactions


def mark_transfer_pair(txn1: Transaction, txn2: Transaction) -> None:
    txn1.status = TransactionStatus.TRANSFER
    txn2.status = TransactionStatus.TRANSFER
    txn1.notes = f"Internal transfer: {txn1.source_bank} <-> {txn2.source_bank}"
    txn2.notes = f"Internal transfer: {txn2.source_bank} <-> {txn1.source_bank}"


def is_transfer_pair(txn1: Transaction, txn2: Transaction) -> bool:
    if txn1.source_bank == txn2.source_bank:
        return False
    if txn1.transaction_date != txn2.transaction_date:
        return False
    if txn1.amount != txn2.amount:
        return False
    return txn1.transaction_type != txn2.transaction_type
