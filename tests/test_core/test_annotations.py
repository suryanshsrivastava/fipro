from datetime import date
from decimal import Decimal

from src.core.annotations import apply_annotations, write_table
from src.models.transactions import Transaction, TransactionType


def _txn(description="UPI-RAVI KUMAR-ravi@ybl-HDFC0001-1-NA", amount="100"):
    return Transaction(date(2025, 1, 2), description, Decimal(amount), TransactionType.DEBIT, "HDFC", "a.xls")


def test_own_annotation_beats_counterparty_rule_and_rule_fills_the_rest(tmp_path):
    labelled, by_rule, unknown = _txn(amount="100"), _txn(amount="200"), _txn("UPI-SOMEONE ELSE-x@ybl-H-1-NA")
    annotations, rules = str(tmp_path / "annotations.csv"), str(tmp_path / "rules.csv")
    write_table(
        annotations,
        "hash",
        ("review_status", "category", "need_want", "frequency", "splitwise", "notes"),
        {
            labelled.hash: {
                "review_status": "reconciled",
                "category": "Family/Rent",
                "splitwise": "yes",
                "notes": "march",
            }
        },
    )
    write_table(
        rules,
        "counterparty",
        ("category", "need_want", "frequency"),
        {"ravi kumar": {"category": "City/Cab", "need_want": "Need", "frequency": "Monthly"}},  # matched upper-cased
    )

    apply_annotations([labelled, by_rule, unknown], annotations, rules)

    assert (labelled.category, labelled.need_want, labelled.frequency) == ("Family/Rent", "Need", "Monthly")
    assert (labelled.review_status, labelled.splitwise, labelled.notes) == ("reconciled", True, "march")
    assert (by_rule.category, by_rule.review_status, by_rule.splitwise) == ("City/Cab", "", False)
    assert (unknown.category, unknown.need_want) == (None, "")


def test_missing_label_files_leave_everything_unlabelled(tmp_path):
    txn = _txn()
    apply_annotations([txn], str(tmp_path / "none.csv"), str(tmp_path / "none2.csv"))
    assert txn.category is None and txn.review_status == ""
