"""Per-folder audit log of statements the pipeline has read (``<bank folder>/audit_log.csv``).

This is the only file the pipeline writes into the input tree. ``date_created`` is the file's mtime the
first time it was logged and is never rewritten; ``date_modified`` is its current mtime, so a row where
the two differ means the statement changed after it was first recorded.
"""

import csv
import logging
import os
from datetime import datetime
from pathlib import Path

from src.models.result import ProcessingResult

logger = logging.getLogger("fipro.audit")
AUDIT_LOG_NAME = "audit_log.csv"
_FIELDS = ["filename", "date_created", "date_modified", "period_start", "period_end", "entries"]


def _mtime(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")


def write_audit_logs(results: list[ProcessingResult]) -> None:
    """Upsert one row per successfully parsed statement into the audit log beside it.

    The script is the only writer. A log that cannot be written (e.g. a read-only folder) is reported
    as a warning and never blocks the export.
    """
    by_dir: dict[Path, list[ProcessingResult]] = {}
    for r in results:
        if not (r.failed or r.warnings):
            by_dir.setdefault(Path(r.source_file).parent, []).append(r)

    for folder, folder_results in by_dir.items():
        try:
            _upsert(folder / AUDIT_LOG_NAME, folder_results)
        except OSError as exc:  # e.g. a read-only folder: the audit is secondary, never block the export
            logger.warning("Could not update %s: %s", folder / AUDIT_LOG_NAME, exc)


def _upsert(log: Path, results: list[ProcessingResult]) -> None:
    rows: dict[str, dict[str, str]] = {}
    if log.exists():
        with log.open(newline="") as f:
            rows = {row["filename"]: row for row in csv.DictReader(f)}

    for r in results:
        path = Path(r.source_file)
        dates = [t.transaction_date for t in r.transactions]
        rows[path.name] = {
            "filename": path.name,
            "date_created": rows.get(path.name, {}).get("date_created") or _mtime(path),
            "date_modified": _mtime(path),
            "period_start": min(dates).isoformat() if dates else "",
            "period_end": max(dates).isoformat() if dates else "",
            "entries": str(len(dates)),
        }

    tmp = log.with_suffix(".tmp")
    with tmp.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows.values(), key=lambda row: row["filename"]))
    os.replace(tmp, log)
