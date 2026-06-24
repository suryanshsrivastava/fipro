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


def main():
    parser = argparse.ArgumentParser(description="Fipro — Bank statement processor")
    parser.add_argument("--config", default="config/config.toml", help="Path to config.toml")
    parser.add_argument("command", nargs="?", default="process", choices=["process", "status", "dashboard", "sheets"])
    parser.add_argument("--csv", default="data/output/goodbudget_export.csv", help="CSV path for dashboard/sheets")
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
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.command == "status":
        cmd_status(config)
    elif args.command == "dashboard":
        cmd_dashboard(args.csv, args.port, args.open)
    elif args.command == "sheets":
        cmd_sheets(args.csv, args.creds, args.title)
    else:
        cmd_process(config)


def cmd_process(config):
    try:
        lines = run_process_command(config)
    except Exception as exc:
        print(f"Processing failed: {exc}", file=sys.stderr)
        sys.exit(1)

    for line in lines:
        print(line)


def cmd_status(config):
    for line in run_status_command(config):
        print(line)


def cmd_dashboard(csv_path: str, port: int, open_browser: bool):
    try:
        launch = prepare_dashboard_launch(csv_path, port, open_browser)
    except CommandInputError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
    for line in launch.lines:
        print(line)
    serve_dashboard(launch.csv_path, launch.port, open_browser=launch.open_browser)


def cmd_sheets(csv_path: str, creds_path: str, title: str):
    try:
        result = run_sheets_command(csv_path, creds_path, title)
    except CommandInputError as exc:
        print(str(exc), file=sys.stderr)
        if "Google credentials not found" in str(exc):
            print("  → Create a service account in Google Cloud Console,", file=sys.stderr)
            print("    enable the Sheets & Drive API, download the JSON key", file=sys.stderr)
            print("    and save it to config/google_credentials.json", file=sys.stderr)
        sys.exit(1)
    for line in result.lines:
        print(line)


if __name__ == "__main__":
    main()
