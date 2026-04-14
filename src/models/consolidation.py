from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from src.models.transactions import Transaction


@dataclass(slots=True)
class BankConsolidation:
    spend: Decimal = Decimal("0")
    income: Decimal = Decimal("0")
    net: Decimal = Decimal("0")
    transfer_total: Decimal = Decimal("0")


@dataclass(slots=True)
class CheckpointMetrics:
    spend: Decimal = Decimal("0")
    income: Decimal = Decimal("0")
    net: Decimal = Decimal("0")
    transfer_total: Decimal = Decimal("0")
    per_bank: dict[str, BankConsolidation] = field(default_factory=dict)
    top_transactions: list[Transaction] = field(default_factory=list)


@dataclass(slots=True)
class WeekCheckpoint:
    week_number: int
    start_date: date
    end_date: date
    transactions: list[Transaction] = field(default_factory=list)
    mtd_transactions: list[Transaction] = field(default_factory=list)

    spend: Decimal = Decimal("0")
    income: Decimal = Decimal("0")
    net: Decimal = Decimal("0")
    transfer_total: Decimal = Decimal("0")
    per_bank: dict[str, BankConsolidation] = field(default_factory=dict)
    top_transactions: list[Transaction] = field(default_factory=list)

    mtd_spend: Decimal = Decimal("0")
    mtd_income: Decimal = Decimal("0")
    mtd_net: Decimal = Decimal("0")
    mtd_transfer_total: Decimal = Decimal("0")
    mtd_per_bank: dict[str, BankConsolidation] = field(default_factory=dict)
    running_balance: Decimal = Decimal("0")


@dataclass(slots=True)
class MonthConsolidation:
    year: int
    month: int
    checkpoints: list[WeekCheckpoint] = field(default_factory=list)

    total_spend: Decimal = Decimal("0")
    total_income: Decimal = Decimal("0")
    total_net: Decimal = Decimal("0")
    transfer_total: Decimal = Decimal("0")
    per_bank: dict[str, BankConsolidation] = field(default_factory=dict)
    running_balance_by_checkpoint: list[Decimal] = field(default_factory=list)
