"""One-off: carry the labels from the old hand-annotated spreadsheets into corpus/state.

Reads corpus/legacy/processed/Expenses_{SBI,Axis}.xlsx and Expensse_HDFC.xlsx, finds each labelled row in the
current export (same bank, date and amount; the running balance breaks ties) and writes its labels to
annotations.csv. Labels already in annotations.csv are never overwritten. A counterparty whose labelled rows
all agree on a Group/Envelope category (at least two of them) is proposed as a row in category_rules.csv.

Run `uv run fipro process` first so corpus/output/dashboard_data.csv carries transaction hashes.
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_settings  # noqa: E402
from src.core.annotations import ANNOTATION_FIELDS, RULE_FIELDS, read_table, write_table  # noqa: E402

LEGACY = Path("corpus/legacy/processed")
STATUSES = ("cleared", "reconciled", "waiting", "doubt")
# (file, bank, date column, debit, credit, balance, status column, free-text columns, need/want, frequency)
SHEETS = (
    ("Expenses_SBI.xlsx", "SBI", "Txn Date", "Debit", "Credit", "Balance", "Column 1", ("Column 2",), None, None),
    ("Expenses_Axis.xlsx", "AXIS", "Tran Date", "Debit", "Credit", "Balance", "Column 1", ("Column 2", "Column 3"), None, None),
    ("Expensse_HDFC.xlsx", "HDFC", "Date", "Withdrawal Amt.", "Deposit Amt.", "Closing Balance", "Column 1", ("Column 2",), "Column 3", "Column 4"),
)  # fmt: skip


def number(value: object) -> float | None:
    try:
        result = float(str(value).replace(",", ""))
    except ValueError:
        return None
    return None if result != result else round(result, 2)  # NaN


def iso_date(value: object) -> str | None:
    if hasattr(value, "year"):
        return pd.Timestamp(value).date().isoformat()  # type: ignore[arg-type]
    for fmt in ("%d/%m/%y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return pd.to_datetime(str(value).strip(), format=fmt).date().isoformat()
        except ValueError:
            continue
    return None


def text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def labels_from(row: pd.Series, status_col, free_cols, need_col, freq_col) -> dict[str, str]:
    status = next((t for t in re.split(r"[,;]", text(row[status_col]).lower()) if t.strip() in STATUSES), "").strip()
    category, notes, splitwise = "", [], False
    for column in free_cols:
        value = text(row[column])
        if not value:
            continue
        splitwise |= "splitwise" in value.lower()
        if "/" in value and not category:
            category = value
        elif value.lower() != "splitwise":
            notes.append(value)
    return {
        "review_status": status,
        "category": category,
        "need_want": text(row[need_col]) if need_col else "",
        "frequency": text(row[freq_col]) if freq_col else "",
        "splitwise": "yes" if splitwise else "",
        "notes": "; ".join(notes),
    }


def main() -> None:
    settings = load_settings()
    current = pd.read_csv(settings.paths.dashboard_data, dtype=str).fillna("")
    current["amount_n"] = current.amount.astype(float).round(2)
    current["balance_n"] = pd.to_numeric(current.balance, errors="coerce").round(2)
    index = defaultdict(list)
    for row in current.itertuples():
        index[(row.source_bank, row.transaction_date, row.amount_n)].append(row)

    annotations = read_table(settings.paths.annotations, "hash")
    seeded = skipped = 0
    for file, bank, date_col, debit_col, credit_col, balance_col, status_col, free_cols, need_col, freq_col in SHEETS:
        old = pd.read_excel(LEGACY / file, sheet_name="main")
        labelled_cols = [status_col, *free_cols, *(c for c in (need_col, freq_col) if c)]
        for _, row in old[old[labelled_cols].notna().any(axis=1)].iterrows():
            debit, credit = number(row[debit_col]), number(row[credit_col])
            amount = credit if credit is not None else (-debit if debit is not None else None)
            matches = index.get((bank, iso_date(row[date_col]), amount), []) if amount is not None else []
            if len(matches) > 1:
                matches = [m for m in matches if m.balance_n == number(row[balance_col])]
            if len(matches) != 1:
                skipped += 1
                continue
            labels = labels_from(row, status_col, free_cols, need_col, freq_col)
            existing = annotations.setdefault(matches[0].hash, {})
            for field in ANNOTATION_FIELDS:
                if labels[field] and not existing.get(field):
                    existing[field] = labels[field]
            seeded += 1
    write_table(settings.paths.annotations, "hash", ANNOTATION_FIELDS, annotations)

    by_counterparty = defaultdict(list)
    hash_to_counterparty = dict(zip(current.hash, current.counterparty, strict=True))
    for txn_hash, row in annotations.items():
        if row.get("category") and hash_to_counterparty.get(txn_hash):
            by_counterparty[hash_to_counterparty[txn_hash]].append(row["category"])
    rules = read_table(settings.paths.category_rules, "counterparty")
    proposed = 0
    for name, categories in by_counterparty.items():
        if len(categories) >= 2 and len(set(categories)) == 1 and name not in rules:
            rules[name] = {"category": categories[0]}
            proposed += 1
    write_table(settings.paths.category_rules, "counterparty", RULE_FIELDS, rules)
    print(
        f"seeded {seeded} labelled rows ({skipped} could not be matched uniquely); proposed {proposed} category rules"
    )


if __name__ == "__main__":
    main()
