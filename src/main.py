import argparse
import sys
from pathlib import Path

from src.config import load_config
from src.core.orchestrator import process_pipeline, discover_files
from src.ui.dashboard import serve_dashboard
from src.exporters.sheets import export_to_google_sheets
from src.utils.logger import setup_logging


def main():
    parser = argparse.ArgumentParser(description='Fipro — Bank statement processor')
    parser.add_argument('--config', default='config/config.toml', help='Path to config.toml')
    parser.add_argument('command', nargs='?', default='process', choices=['process', 'status', 'dashboard', 'sheets'])
    parser.add_argument('--csv', default='data/output/goodbudget_export.csv', help='CSV path for dashboard/sheets')
    parser.add_argument('--port', type=int, default=8080, help='Dashboard port (default: 8080)')
    parser.add_argument('--creds', default='config/google_credentials.json', help='Google service account credentials JSON')
    parser.add_argument('--title', default='Fipro Transactions', help='Spreadsheet title for sheets export')
    parser.add_argument('--open', action='store_true', help='Open dashboard automatically')
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        setup_logging(config.get('fipro', {}).get('log_level', 'INFO'))
    except FileNotFoundError as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f'Config error: {e}', file=sys.stderr)
        sys.exit(1)

    if args.command == 'status':
        cmd_status(config)
    elif args.command == 'dashboard':
        cmd_dashboard(args.csv, args.port, args.open)
    elif args.command == 'sheets':
        cmd_sheets(args.csv, args.creds, args.title)
    else:
        cmd_process(config)


def cmd_process(config):
    results = process_pipeline(config)
    total = sum(r.successful for r in results)
    failed = sum(len(r.errors) for r in results)
    print(f'Processed {len(results)} files. {total} transactions. {failed} errors.')


def cmd_status(config):
    files = discover_files(config)
    if not files:
        print('No files to process.')
        return
    by_bank = {}
    for f in files:
        bank = f.metadata.get('bank', 'UNKNOWN')
        by_bank.setdefault(bank, []).append(f.filename)
    for bank, names in sorted(by_bank.items()):
        print(f'{bank}: {len(names)} file(s)')
        for n in names:
            print(f'  - {n}')


def cmd_dashboard(csv_path: str, port: int, open_browser: bool):
    p = Path(csv_path)
    if not p.exists():
        print(f'CSV not found: {csv_path} — run `fipro process` first.', file=sys.stderr)
        sys.exit(1)
    print(f'Starting dashboard on http://localhost:{port} ...')
    serve_dashboard(csv_path, port)


def cmd_sheets(csv_path: str, creds_path: str, title: str):
    p = Path(csv_path)
    if not p.exists():
        print(f'CSV not found: {csv_path} — run `fipro process` first.', file=sys.stderr)
        sys.exit(1)
    c = Path(creds_path)
    if not c.exists():
        print(f'Google credentials not found: {creds_path}', file=sys.stderr)
        print('  → Create a service account in Google Cloud Console,', file=sys.stderr)
        print('    enable the Sheets & Drive API, download the JSON key', file=sys.stderr)
        print('    and save it to config/google_credentials.json', file=sys.stderr)
        sys.exit(1)
    url = export_to_google_sheets(csv_path, creds_path, title)
    print(f'Done. Open: {url}')


if __name__ == '__main__':
    main()
