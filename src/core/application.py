import csv
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.config import GmailSettings, Settings
from src.connectors.gmail import authorize, fetch_password_hints, gmail_service, save_password_hints
from src.core.ingestion import discover_files
from src.core.orchestrator import process_pipeline
from src.core.statement_passwords import load_statement_passwords
from src.core.suggestions import suggest_categories
from src.exporters.report import summarize_pipeline_run
from src.exporters.sheets import export_to_google_sheets


class CommandInputError(ValueError):
    pass


@dataclass(slots=True)
class DashboardLaunch:
    csv_path: str
    port: int
    open_browser: bool
    lines: list[str]


@dataclass(slots=True)
class SheetsCommandResult:
    url: str
    lines: list[str]


def run_process_command(settings: Settings) -> list[str]:
    """Process statements, using any saved statement passwords (dashboard/inline passwords still win)."""
    passwords = load_statement_passwords(settings.paths.statement_passwords)
    return summarize_pipeline_run(process_pipeline(settings, passwords=passwords))


def run_suggest_command(settings: Settings, endpoint: str, limit: int | None) -> list[str]:
    """Score counterparties with a local decision model; `fipro dashboard` then offers the confident answers."""
    if not Path(settings.paths.dashboard_data).exists():
        raise CommandInputError(f"{settings.paths.dashboard_data} not found. Run `fipro process` first.")
    try:
        scored = suggest_categories(
            endpoint,
            settings.paths.dashboard_data,
            settings.paths.annotations,
            settings.paths.category_rules,
            settings.paths.suggestions,
            limit,
        )
    except OSError as exc:
        raise CommandInputError(f"Could not reach the model at {endpoint}: {exc}") from exc
    except ValueError as exc:
        raise CommandInputError(str(exc)) from exc
    return [f"Scored {scored} counterpart{'y' if scored == 1 else 'ies'} → {settings.paths.suggestions}"]


def _require_existing_file(
    path: str,
    *,
    error_message: str,
    path_exists: Callable[[Path], bool],
) -> None:
    if not path_exists(Path(path)):
        raise CommandInputError(error_message)


def run_status_command(
    settings: Settings,
    *,
    discoverer: Callable[[Settings], list] = discover_files,
) -> list[str]:
    files = discoverer(settings)
    if not files:
        return ["No files to process."]

    by_bank: dict[str, list[str]] = {}
    for crawled_file in files:
        bank = crawled_file.metadata.get("bank", "UNKNOWN")
        by_bank.setdefault(bank, []).append(crawled_file.filename)

    lines: list[str] = []
    for bank, names in sorted(by_bank.items()):
        lines.append(f"{bank}: {len(names)} file(s)")
        lines.extend(f"  - {name}" for name in names)
    return lines


def run_latest_command(settings: Settings, *, today: date | None = None) -> list[str]:
    """Per bank, the newest transaction date in the last export: download statements from there onwards."""
    path = Path(settings.paths.dashboard_data)
    if not path.exists():
        raise CommandInputError(f"{path} not found. Run `fipro process` first.")
    today = today or date.today()
    spans: dict[str, list[str]] = {}
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("transaction_date"):
                spans.setdefault(row["source_bank"], []).append(row["transaction_date"])
    lines = []
    for bank, dates in sorted(spans.items()):
        last = date.fromisoformat(max(dates))
        lines.append(f"{bank}: latest transaction {last} ({(today - last).days} days ago); download {last} to {today}")
    lines = lines or ["No transactions in the export."]
    for bank, start, end in statement_gaps(settings.paths.input):
        lines.append(f"{bank}: no statement covers {start} to {end}; download it")
    return lines


def statement_gaps(corpus: str, min_days: int = 31) -> list[tuple[str, date, date]]:
    """Stretches longer than ``min_days`` that no statement's period covers, from each bank's audit_log.csv.

    A statement's period runs from its first to its last transaction, so a shorter silence is ordinary inactivity.
    """
    gaps: list[tuple[str, date, date]] = []
    for log in sorted(Path(corpus).glob("*/audit_log.csv")):
        with open(log, newline="") as f:
            periods = sorted(
                (date.fromisoformat(r["period_start"]), date.fromisoformat(r["period_end"]))
                for r in csv.DictReader(f)
                if r.get("period_start") and r.get("period_end")
            )
        covered_to = None
        for start, end in periods:
            if covered_to is not None and (start - covered_to).days > min_days:
                gaps.append((log.parent.name.upper(), covered_to + timedelta(days=1), start - timedelta(days=1)))
            covered_to = max(covered_to, end) if covered_to else end
    return gaps


def prepare_dashboard_launch(
    csv_path: str,
    port: int,
    open_browser: bool,
    *,
    path_exists: Callable[[Path], bool] | None = None,
) -> DashboardLaunch:
    exists = path_exists or Path.exists
    lines = [f"Starting dashboard on http://localhost:{port} ..."]
    if not exists(Path(csv_path)):
        # Still start: locked statements can be unlocked and processed from the dashboard.
        lines.append(f"No transactions yet ({csv_path} not found); showing locked statements only.")

    return DashboardLaunch(csv_path=csv_path, port=port, open_browser=open_browser, lines=lines)


def run_gmail_command(gmail: GmailSettings, hints_path: str, *, service: Any = None) -> list[str]:
    """Fetch statement password hints from Gmail and save them for the dashboard."""
    queries = gmail.queries
    if not queries:
        raise CommandInputError("No Gmail search queries configured under [gmail.queries] in config.toml")
    if service is None:
        creds = authorize(
            gmail.credentials,
            gmail.token,
        )
        service = gmail_service(creds)

    hints = fetch_password_hints(service, queries, max_messages=gmail.max_messages)
    save_password_hints(hints, hints_path)

    found = {hint.bank: hint for hint in hints}
    lines = []
    for bank in sorted(bank.upper() for bank in queries):
        if bank in found:
            hint = found[bank]
            lines.append(f"{bank}: {hint.hint}  (email of {hint.received}: {hint.subject!r})")
        else:
            lines.append(f"{bank}: no password hint found in Gmail")
    lines.append(f"Saved to {hints_path}")
    return lines


def run_sheets_command(
    csv_path: str,
    creds_path: str,
    title: str,
    *,
    path_exists: Callable[[Path], bool] | None = None,
    exporter: Callable[[str, str, str], str] = export_to_google_sheets,
) -> SheetsCommandResult:
    exists = path_exists or Path.exists
    _require_existing_file(
        csv_path,
        error_message=f"CSV not found: {csv_path} — run `fipro process` first.",
        path_exists=exists,
    )
    _require_existing_file(
        creds_path,
        error_message=f"Google credentials not found: {creds_path}",
        path_exists=exists,
    )

    url = exporter(csv_path, creds_path, title)
    return SheetsCommandResult(url=url, lines=[f"Done. Open: {url}"])
