import argparse
import sys

from src.config import Settings, load_settings
from src.core.application import (
    CommandInputError,
    prepare_dashboard_launch,
    run_gmail_alerts_command,
    run_gmail_command,
    run_gmail_statements_command,
    run_latest_command,
    run_process_command,
    run_sheets_command,
    run_status_command,
    run_suggest_command,
)
from src.ui.dashboard import serve_dashboard
from src.utils.logger import setup_logging


def _print_lines(lines: list[str]) -> None:
    for line in lines:
        print(line)


def _exit_with_error(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Fipro — Bank statement processor")
    parser.add_argument("--config", default="config/config.toml", help="Path to config.toml")
    parser.add_argument(
        "command",
        nargs="?",
        default="process",
        choices=["process", "status", "dashboard", "sheets", "gmail", "suggest", "latest"],
    )
    parser.add_argument("--csv", default=None, help="CSV path override for dashboard or sheets")
    parser.add_argument("--port", type=int, default=8080, help="Dashboard port (default: 8080)")
    parser.add_argument(
        "--creds", default="config/google_credentials.json", help="Google service account credentials JSON"
    )
    parser.add_argument("--title", default="Fipro Transactions", help="Spreadsheet title for sheets export")
    parser.add_argument(
        "--endpoint", default="http://127.0.0.1:9931", help="Local llama.cpp server for `suggest` (must be localhost)"
    )
    parser.add_argument("--limit", type=int, default=None, help="Score at most this many counterparties in `suggest`")
    parser.add_argument("--alerts", action="store_true", help="With `gmail`: learn payment times from UPI alert emails")
    parser.add_argument(
        "--statements", action="store_true", help="With `gmail`: save statement attachments to the corpus"
    )
    parser.add_argument("--open", action="store_true", help="Open dashboard automatically")
    args = parser.parse_args()

    try:
        settings = load_settings(args.config)
        setup_logging(settings.log_level)
    except FileNotFoundError as e:
        _exit_with_error(f"Error: {e}")
    except ValueError as e:
        _exit_with_error(f"Config error: {e}")

    if args.command == "status":
        cmd_status(settings)
    elif args.command == "dashboard":
        dashboard_csv = args.csv or settings.paths.dashboard_data
        cmd_dashboard(settings, dashboard_csv, args.port, args.open)
    elif args.command == "sheets":
        sheets_csv = args.csv or f"{settings.paths.output}/goodbudget_export.csv"
        cmd_sheets(sheets_csv, args.creds, args.title)
    elif args.command == "latest":
        try:
            _print_lines(run_latest_command(settings))
        except CommandInputError as exc:
            _exit_with_error(str(exc))
    elif args.command == "gmail":
        cmd_gmail(settings, args.statements, args.alerts)
    elif args.command == "suggest":
        cmd_suggest(settings, args.endpoint, args.limit)
    else:
        cmd_process(settings)


def cmd_process(settings: Settings):
    try:
        lines = run_process_command(settings)
    except Exception as exc:
        _exit_with_error(f"Processing failed: {exc}")
    _print_lines(lines)


def cmd_status(settings: Settings):
    _print_lines(run_status_command(settings))


def cmd_dashboard(settings: Settings, csv_path: str, port: int, open_browser: bool):
    try:
        launch = prepare_dashboard_launch(csv_path, port, open_browser)
    except CommandInputError as exc:
        _exit_with_error(str(exc))
    _print_lines(launch.lines)
    serve_dashboard(launch.csv_path, launch.port, open_browser=launch.open_browser, settings=settings)


def cmd_sheets(csv_path: str, creds_path: str, title: str):
    try:
        result = run_sheets_command(csv_path, creds_path, title)
    except CommandInputError as exc:
        message = str(exc)
        print(message, file=sys.stderr)
        if "Google credentials not found" in message:
            print("  → Create a service account in Google Cloud Console,", file=sys.stderr)
            print("    enable the Sheets & Drive API, download the JSON key", file=sys.stderr)
            print("    and save it to config/google_credentials.json", file=sys.stderr)
        sys.exit(1)
    _print_lines(result.lines)


def cmd_suggest(settings: Settings, endpoint: str, limit: int | None):
    try:
        lines = run_suggest_command(settings, endpoint, limit)
    except CommandInputError as exc:
        _exit_with_error(str(exc))
    _print_lines(lines)


def cmd_gmail(settings: Settings, statements: bool = False, alerts: bool = False):
    try:
        if alerts:
            lines = run_gmail_alerts_command(settings.gmail, settings.paths.txn_times)
        elif statements:
            lines = run_gmail_statements_command(settings.gmail, settings.paths.input)
        else:
            lines = run_gmail_command(settings.gmail, settings.paths.password_hints)
    except (CommandInputError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        if isinstance(exc, FileNotFoundError):
            print("  → In Google Cloud Console: enable the Gmail API, create an OAuth client", file=sys.stderr)
            print("    of type 'Desktop app', download its JSON and save it as", file=sys.stderr)
            print("    config/gmail_credentials.json (path set by [gmail].credentials).", file=sys.stderr)
        sys.exit(1)
    _print_lines(lines)


if __name__ == "__main__":
    main()
