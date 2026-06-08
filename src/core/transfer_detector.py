from src.models.transactions import Transaction, TransactionStatus


def detect_transfers(transactions: list[Transaction]) -> list[Transaction]:
    for i, t1 in enumerate(transactions):
        if t1.status == TransactionStatus.TRANSFER:
            continue
        for t2 in transactions[i + 1 :]:
            if t2.status == TransactionStatus.TRANSFER:
                continue
            if is_transfer_pair(t1, t2):
                t1.status = TransactionStatus.TRANSFER
                t2.status = TransactionStatus.TRANSFER
                t1.notes = f"Internal transfer: {t1.source_bank} <-> {t2.source_bank}"
                t2.notes = f"Internal transfer: {t2.source_bank} <-> {t1.source_bank}"
    return transactions


def is_transfer_pair(txn1: Transaction, txn2: Transaction) -> bool:
    if txn1.source_bank == txn2.source_bank:
        return False
    if txn1.transaction_date != txn2.transaction_date:
        return False
    if txn1.amount != txn2.amount:
        return False
    return txn1.transaction_type != txn2.transaction_type
