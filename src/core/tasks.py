"""A to-do list built from what the data shows, plus tasks you add yourself.

Insight tasks are recomputed on every request and carry an id that names the condition they stem from (a bill and
its due date, a month, a count). When the condition changes the id changes, so a task you finished does not hide
a new one. ``corpus/state/tasks.csv`` keeps only your side: status and note per id, and the manual tasks.

Each task is for ``you`` (a payment, a call to the bank) or ``agent`` (reading and preparing work that needs no
judgement from you); an agent task carries a self-contained prompt to hand over. Nothing here acts on its own.
"""

import time
from collections import defaultdict
from datetime import date

from src.core.annotations import read_table, write_table
from src.core.monthly import available_months, default_month, month_summary
from src.utils.narration import CARD_BANKS

STATUSES = ("open", "doing", "done", "dismissed")
OWNERS = ("you", "agent")
TASK_FIELDS = ("status", "note", "title", "detail", "owner", "priority")
_TRANSFER = "internal_transfer"


def _amount(row: dict) -> float:
    try:
        return float(row.get("amount") or 0)
    except ValueError:
        return 0.0


def _inr(n: float) -> str:
    return f"₹{round(n):,}"


def _task(id_: str, title: str, detail: str, owner: str, priority: int, prompt: str = "") -> dict:
    return {
        "id": id_,
        "title": title,
        "detail": detail,
        "owner": owner,
        "priority": priority,
        "prompt": prompt,
        "manual": False,
    }


def insight_tasks(rows: list[dict], dues: list[dict], gaps: list[tuple], today: date, repo: str = ".") -> list[dict]:
    """Tasks the current data implies; ``dues`` is ``card_dues`` output, ``gaps`` is ``statement_gaps`` output."""
    tasks: list[dict] = []
    for card in dues:
        if card["paid"]:
            continue
        when = (
            f"overdue by {-card['days']} day(s)"
            if card["days"] < 0
            else ("due today" if card["days"] == 0 else f"due in {card['days']} day(s)")
        )
        tasks.append(
            _task(
                f"bill:{card['bank']}:{card['due']}",
                f"Pay the {card['bank']} bill, {_inr(card['total'])}",
                f"Due {card['due']}, {when}. No payment since the statement is in your data yet.",
                "you",
                1 if card["days"] <= 3 else 2,
            )
        )

    since = today.toordinal() - 90
    fees = [
        r
        for r in rows
        if r.get("source_bank") in CARD_BANKS
        and r.get("description", "").upper().startswith("LATE FEE")
        and date.fromisoformat(r["transaction_date"]).toordinal() >= since
    ]
    if fees:
        total = sum(-_amount(r) for r in fees) * 1.18
        tasks.append(
            _task(
                f"latefee:{max(r['transaction_date'] for r in fees)}",
                "Stop paying late fees: set autopay on your cards",
                f"{len(fees)} late fee(s) in 90 days, about {_inr(total)} with GST. Autopay for at least the minimum due avoids them.",
                "you",
                1,
            )
        )

    months = available_months(rows)
    month = default_month(months, today)
    if month:
        summary = month_summary(rows, month)
        unl = summary["uncategorised"]
        if unl["count"]:
            tasks.append(
                _task(
                    f"label:{month}:{unl['count']}",
                    f"Label {unl['count']} uncategorised payments in {month} ({_inr(unl['amount'])})",
                    "Open the Review tab for the month. An agent can propose categories first; you approve them.",
                    "agent",
                    2,
                    f"In the Fipro repo at {repo}, read corpus/output/dashboard_data.csv. For {month}, list every spend row with no category (skip internal_transfer), grouped by counterparty. For each group propose one category from those already used in corpus/state/annotations.csv and category_rules.csv, using evidence from other months, corpus/state/rides.csv and the time of day. Output a table with payee, rows, total, proposed category and confidence. Do not write to corpus/state.",
                )
            )
        if summary["saved"] < 0:
            top = ", ".join(f"{c['name']} {_inr(c['amount'])}" for c in summary["by_category"][:3])
            tasks.append(
                _task(
                    f"overspend:{month}",
                    f"{month}: spent {_inr(-summary['saved'])} more than earned",
                    f"Largest categories: {top}. Decide what to cut or whether it was one-off.",
                    "you",
                    2,
                )
            )

    latest: dict[str, str] = defaultdict(str)
    for r in rows:
        if r.get("source_bank") not in CARD_BANKS and r.get("transaction_date", "") > latest[r["source_bank"]]:
            latest[r["source_bank"]] = r["transaction_date"]
    for bank, last in sorted(latest.items()):
        if (today - date.fromisoformat(last)).days > 14:
            tasks.append(
                _task(
                    f"stmt:{bank}:{last}",
                    f"Download the {bank} statement from {last}",
                    f"Latest {bank} transaction is {(today - date.fromisoformat(last)).days} days old. Drop the file in data/{bank.lower()}/ and run fipro process.",
                    "you",
                    3,
                )
            )
    for bank, start, end in gaps:
        tasks.append(
            _task(
                f"gap:{bank}:{start}",
                f"Download the missing {bank} statement for {start} to {end}",
                "No statement in the corpus covers this stretch.",
                "you",
                3,
            )
        )

    work = [
        r
        for r in rows
        if str(r.get("category", "")).startswith("Work/")
        and r.get("category") != "Work/Income"
        and r.get("status") != _TRANSFER
        and not r.get("reimbursement")
        and (_amount(r) < 0 or r.get("source_bank") in CARD_BANKS)
    ]
    if work:
        total = sum(-_amount(r) for r in work)
        tasks.append(
            _task(
                f"work:{len(work)}",
                f"File {len(work)} Work/* expenses for reimbursement ({_inr(total)})",
                "Open the Work claims tab: download the CSV, then mark them as filed.",
                "agent",
                2,
                f"In the Fipro repo at {repo}, read corpus/output/dashboard_data.csv. List every row whose category starts with Work/ (except Work/Income) and whose reimbursement column is empty. Build a claim sheet with date, payee, amount, category and the matching Uber or Rapido receipt note, and a total. Output it as a CSV in .amp/in/ and show me the total. Do not file anything or change corpus/state.",
            )
        )

    detected = [r for r in rows if r.get("frequency_detected") == "yes"]
    if detected:
        payees = len({r.get("counterparty") for r in detected})
        tasks.append(
            _task(
                f"recurring:{len(detected)}",
                f"Confirm {len(detected)} detected recurring payments ({payees} payees)",
                "Transactions tab, frequency filter 'Detected monthly', then ✓ per payee.",
                "you",
                3,
            )
        )
    return sorted(tasks, key=lambda t: t["priority"])


def load_state(path: str) -> dict[str, dict[str, str]]:
    return read_table(path, "id")


def manual_tasks(state: dict[str, dict[str, str]]) -> list[dict]:
    return [
        {
            "id": k,
            "title": v.get("title", ""),
            "detail": v.get("detail", ""),
            "owner": v.get("owner") or "you",
            "priority": int(v.get("priority") or 2),
            "prompt": "",
            "manual": True,
        }
        for k, v in state.items()
        if k.startswith("manual:")
    ]


def all_tasks(
    rows: list[dict], dues: list[dict], gaps: list[tuple], today: date, path: str, repo: str = "."
) -> list[dict]:
    """Insight and manual tasks with the status and note you saved, open ones first."""
    state = load_state(path)
    tasks = insight_tasks(rows, dues, gaps, today, repo) + manual_tasks(state)
    for t in tasks:
        saved = state.get(t["id"], {})
        t["status"], t["note"] = saved.get("status") or "open", saved.get("note", "")
    return sorted(tasks, key=lambda t: (t["status"] in ("done", "dismissed"), t["priority"]))


def set_task(path: str, task_id: str, *, status: str | None = None, note: str | None = None) -> None:
    if status is not None and status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    if note is not None and len(note) > 500:
        raise ValueError("note is longer than 500 characters")
    if not task_id or len(task_id) > 200:
        raise ValueError("bad task id")
    rows = read_table(path, "id")
    row = rows.setdefault(task_id, {})
    if status is not None:
        row["status"] = status
    if note is not None:
        row["note"] = note.strip()
    write_table(path, "id", TASK_FIELDS, rows)


def add_task(path: str, title: str, detail: str = "", owner: str = "you", priority: int = 2) -> str:
    title = title.strip()
    if not title or len(title) > 200 or len(detail) > 500 or owner not in OWNERS or priority not in (1, 2, 3):
        raise ValueError("a title (up to 200 characters), an owner of you or agent and a priority of 1-3 are required")
    task_id = f"manual:{int(time.time() * 1000)}"
    rows = read_table(path, "id")
    rows[task_id] = {
        "status": "open",
        "title": title,
        "detail": detail.strip(),
        "owner": owner,
        "priority": str(priority),
    }
    write_table(path, "id", TASK_FIELDS, rows)
    return task_id
