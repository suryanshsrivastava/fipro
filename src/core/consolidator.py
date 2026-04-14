from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal

from src.models.consolidation import (
    BankConsolidation,
    CheckpointMetrics,
    MonthConsolidation,
    WeekCheckpoint,
)
from src.models.transactions import Transaction, TransactionStatus


def build_saturday_checkpoints(year: int, month: int) -> list[tuple[date, date]]:
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    checkpoints: list[tuple[date, date]] = []

    current_start = start
    while current_start <= end:
        days_until_saturday = (5 - current_start.weekday()) % 7
        current_end = min(current_start + timedelta(days=days_until_saturday), end)
        checkpoints.append((current_start, current_end))
        current_start = current_end + timedelta(days=1)

    return checkpoints


def _is_transfer(transaction: Transaction) -> bool:
    return transaction.status == TransactionStatus.TRANSFER


def _empty_bank() -> BankConsolidation:
    return BankConsolidation()


def compute_checkpoint_metrics(
    transactions: list[Transaction], top_n: int = 5
) -> CheckpointMetrics:
    spend = Decimal("0")
    income = Decimal("0")
    transfer_total = Decimal("0")
    per_bank: dict[str, BankConsolidation] = {}

    for transaction in transactions:
        if transaction.source_bank not in per_bank:
            per_bank[transaction.source_bank] = _empty_bank()

        bank_data = per_bank[transaction.source_bank]
        signed_amount = transaction.signed_amount

        if _is_transfer(transaction):
            amount_abs = abs(signed_amount)
            transfer_total += amount_abs
            bank_data.transfer_total += amount_abs
            continue

        if signed_amount < 0:
            spend += abs(signed_amount)
            bank_data.spend += abs(signed_amount)
        else:
            income += signed_amount
            bank_data.income += signed_amount

        bank_data.net += signed_amount

    for bank_data in per_bank.values():
        bank_data.net = bank_data.income - bank_data.spend

    net = income - spend
    top_transactions = sorted(
        transactions,
        key=lambda txn: abs(txn.signed_amount),
        reverse=True,
    )[:top_n]

    return CheckpointMetrics(
        spend=spend,
        income=income,
        net=net,
        transfer_total=transfer_total,
        per_bank=per_bank,
        top_transactions=top_transactions,
    )


def build_month_consolidation(
    transactions: list[Transaction], year: int, month: int, top_n: int = 5
) -> MonthConsolidation:
    monthly_transactions = [
        transaction
        for transaction in transactions
        if transaction.transaction_date.year == year and transaction.transaction_date.month == month
    ]
    monthly_transactions.sort(key=lambda txn: txn.transaction_date)

    checkpoints: list[WeekCheckpoint] = []
    running_balance_by_checkpoint: list[Decimal] = []

    for week_number, (start_date, end_date) in enumerate(build_saturday_checkpoints(year, month), start=1):
        week_transactions = [
            transaction
            for transaction in monthly_transactions
            if start_date <= transaction.transaction_date <= end_date
        ]
        mtd_transactions = [
            transaction for transaction in monthly_transactions if transaction.transaction_date <= end_date
        ]

        week_metrics = compute_checkpoint_metrics(week_transactions, top_n=top_n)
        mtd_metrics = compute_checkpoint_metrics(mtd_transactions, top_n=top_n)
        running_balance = mtd_metrics.net
        running_balance_by_checkpoint.append(running_balance)

        checkpoints.append(
            WeekCheckpoint(
                week_number=week_number,
                start_date=start_date,
                end_date=end_date,
                transactions=week_transactions,
                mtd_transactions=mtd_transactions,
                spend=week_metrics.spend,
                income=week_metrics.income,
                net=week_metrics.net,
                transfer_total=week_metrics.transfer_total,
                per_bank=week_metrics.per_bank,
                top_transactions=week_metrics.top_transactions,
                mtd_spend=mtd_metrics.spend,
                mtd_income=mtd_metrics.income,
                mtd_net=mtd_metrics.net,
                mtd_transfer_total=mtd_metrics.transfer_total,
                mtd_per_bank=mtd_metrics.per_bank,
                running_balance=running_balance,
            )
        )

    month_metrics = compute_checkpoint_metrics(monthly_transactions, top_n=top_n)
    return MonthConsolidation(
        year=year,
        month=month,
        checkpoints=checkpoints,
        total_spend=month_metrics.spend,
        total_income=month_metrics.income,
        total_net=month_metrics.net,
        transfer_total=month_metrics.transfer_total,
        per_bank=month_metrics.per_bank,
        running_balance_by_checkpoint=running_balance_by_checkpoint,
    )
