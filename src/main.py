import argparse
import sys

from src.config import load_config
from src.core.application import (
    CommandInputError,
    prepare_dashboard_launch,
    run_process_command,
    run_sheets_command,
    run_status_command,
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
    parser.add_argument("command", nargs="?", default="process", choices=["process", "status", "dashboard", "sheets"])
    parser.add_argument("--csv", default=None, help="CSV path override for dashboard or sheets")
    parser.add_argument("--port", type=int, default=8080, help="Dashboard port (default: 8080)")
    parser.add_argument(
        "--creds", default="config/google_credentials.json", help="Google service account credentials JSON"
    )
    parser.add_argument("--title", default="Fipro Transactions", help="Spreadsheet title for sheets export")
    parser.add_argument("--open", action="store_true", help="Open dashboard automatically")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        setup_logging(config.get("fipro", {}).get("log_level", "INFO"))
    except FileNotFoundError as e:
        _exit_with_error(f"Error: {e}")
    except ValueError as e:
        _exit_with_error(f"Config error: {e}")

    if args.command == "status":
        cmd_status(config)
    elif args.command == "dashboard":
        dashboard_csv = args.csv or config.get("paths", {}).get("dashboard_data", "data/output/dashboard_data.csv")
        cmd_dashboard(dashboard_csv, args.port, args.open)
    elif args.command == "sheets":
        sheets_csv = args.csv or f"{config.get('paths', {}).get('output', 'data/output')}/goodbudget_export.csv"
        cmd_sheets(sheets_csv, args.creds, args.title)
    else:
        cmd_process(config)


def cmd_process(config):
    try:
        lines = run_process_command(config)
    except Exception as exc:
        _exit_with_error(f"Processing failed: {exc}")
    _print_lines(lines)


def cmd_status(config):
    _print_lines(run_status_command(config))


def cmd_dashboard(csv_path: str, port: int, open_browser: bool):
    try:
        launch = prepare_dashboard_launch(csv_path, port, open_browser)
    except CommandInputError as exc:
        _exit_with_error(str(exc))
    _print_lines(launch.lines)
    serve_dashboard(launch.csv_path, launch.port, open_browser=launch.open_browser)


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


if __name__ == "__main__":
    main()
