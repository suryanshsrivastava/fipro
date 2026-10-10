from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.connectors.gmail import authorize, fetch_password_hints, gmail_service, save_password_hints
from src.core.ingestion import discover_files
from src.core.orchestrator import process_pipeline
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


def run_process_command(config: dict) -> list[str]:
    return summarize_pipeline_run(process_pipeline(config))


def _require_existing_file(
    path: str,
    *,
    error_message: str,
    path_exists: Callable[[Path], bool],
) -> None:
    if not path_exists(Path(path)):
        raise CommandInputError(error_message)


def run_status_command(
    config: dict,
    *,
    discoverer: Callable[[dict], list] = discover_files,
) -> list[str]:
    files = discoverer(config)
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


def run_gmail_command(config: dict, *, service: Any = None) -> list[str]:
    """Fetch statement password hints from Gmail and save them for the dashboard."""
    gmail_config = config.get("gmail", {})
    queries = gmail_config.get("queries", {})
    if not queries:
        raise CommandInputError("No Gmail search queries configured under [gmail.queries] in config.toml")
    if service is None:
        creds = authorize(
            gmail_config.get("credentials", "config/gmail_credentials.json"),
            gmail_config.get("token", "config/gmail_token.json"),
        )
        service = gmail_service(creds)

    hints = fetch_password_hints(service, queries, max_messages=gmail_config.get("max_messages", 10))
    hints_path = config.get("paths", {}).get("password_hints", "data/password_hints.json")
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
