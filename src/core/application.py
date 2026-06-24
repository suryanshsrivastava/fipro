from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
    run = process_pipeline(config)
    return summarize_pipeline_run(run)


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
    csv = Path(csv_path)
    if not exists(csv):
        raise CommandInputError(f"CSV not found: {csv_path} — run `fipro process` first.")

    return DashboardLaunch(
        csv_path=csv_path,
        port=port,
        open_browser=open_browser,
        lines=[f"Starting dashboard on http://localhost:{port} ..."],
    )


def run_sheets_command(
    csv_path: str,
    creds_path: str,
    title: str,
    *,
    path_exists: Callable[[Path], bool] | None = None,
    exporter: Callable[[str, str, str], str] = export_to_google_sheets,
) -> SheetsCommandResult:
    exists = path_exists or Path.exists
    csv = Path(csv_path)
    creds = Path(creds_path)

    if not exists(csv):
        raise CommandInputError(f"CSV not found: {csv_path} — run `fipro process` first.")
    if not exists(creds):
        raise CommandInputError(f"Google credentials not found: {creds_path}")

    url = exporter(csv_path, creds_path, title)
    return SheetsCommandResult(url=url, lines=[f"Done. Open: {url}"])
