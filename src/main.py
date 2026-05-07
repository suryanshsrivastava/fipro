import argparse
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.config import load_config
from src.core.consolidator import build_month_consolidation
from src.core.orchestrator import process_pipeline, discover_files
from src.ui.dashboard import serve_dashboard
from src.exporters.sheets import export_to_google_sheets
from src.utils.utils import load_transactions_from_goodbudget_csv
from src.utils.logger import setup_logging


def main():
    parser = argparse.ArgumentParser(description='Fipro — Bank statement processor')
    parser.add_argument('--config', default='config/config.toml', help='Path to config.toml')
    parser.add_argument('command', nargs='?', default='process', choices=['process', 'status', 'dashboard', 'sheets', 'summary'])
    parser.add_argument('--csv', default='data/output/goodbudget_export.csv', help='CSV path for dashboard/sheets')
    parser.add_argument('--port', type=int, default=8080, help='Dashboard port (default: 8080)')
    parser.add_argument('--creds', default='config/google_credentials.json', help='Google service account credentials JSON')
    parser.add_argument('--title', default='Fipro Transactions', help='Spreadsheet title for sheets export')
    parser.add_argument('--open', action='store_true', help='Open dashboard automatically')
    parser.add_argument('--month', default='', help='Month for summary in YYYY-MM format')
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
        cmd_dashboard(args.csv, args.port, args.open, config)
    elif args.command == 'sheets':
        cmd_sheets(args.csv, args.creds, args.title)
    elif args.command == 'summary':
        cmd_summary(args.csv, args.month, config)
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


def cmd_dashboard(csv_path: str, port: int, open_browser: bool, config: dict):
    p = Path(csv_path)
    if not p.exists():
        print(f'CSV not found: {csv_path} — run `fipro process` first.', file=sys.stderr)
        sys.exit(1)
    summary_top_n = config.get("summary", {}).get("top_n", 5)
    print(f'Starting dashboard on http://localhost:{port} ...')
    serve_dashboard(csv_path, port, summary_top_n=summary_top_n, open_browser=open_browser)


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


def _fmt_amount(amount: Decimal) -> str:
    sign = "+" if amount >= 0 else "-"
    return f"{sign}{abs(amount):,.2f}"


def cmd_summary(csv_path: str, month_value: str, config: dict):
    path = Path(csv_path)
    if not path.exists():
        print(f'CSV not found: {csv_path} — run `fipro process` first.', file=sys.stderr)
        sys.exit(1)

    if month_value:
        try:
            parsed_month = datetime.strptime(month_value, "%Y-%m")
            year = parsed_month.year
            month = parsed_month.month
        except ValueError:
            print('Invalid --month value. Expected format YYYY-MM.', file=sys.stderr)
            sys.exit(1)
    else:
        now = datetime.now()
        year = now.year
        month = now.month

    top_n = config.get("summary", {}).get("top_n", 5)
    transactions = load_transactions_from_goodbudget_csv(csv_path)
    consolidation = build_month_consolidation(transactions, year, month, top_n=top_n)
    month_label = datetime(year, month, 1).strftime("%B %Y")

    print(f"{month_label} -- Monthly Consolidation")
    print("=" * 52)
    for checkpoint in consolidation.checkpoints:
        print(
            f"Week {checkpoint.week_number} "
            f"({checkpoint.start_date.isoformat()} to {checkpoint.end_date.isoformat()})"
        )
        print(f"  Week Spend      {_fmt_amount(-checkpoint.spend)}")
        print(f"  Week Income     {_fmt_amount(checkpoint.income)}")
        print(f"  Week Net        {_fmt_amount(checkpoint.net)}")
        print(f"  Week Transfers  {_fmt_amount(checkpoint.transfer_total)}")
        print(f"  MTD Spend       {_fmt_amount(-checkpoint.mtd_spend)}")
        print(f"  MTD Income      {_fmt_amount(checkpoint.mtd_income)}")
        print(f"  MTD Net         {_fmt_amount(checkpoint.mtd_net)}")
        print(f"  Running Balance {_fmt_amount(checkpoint.running_balance)}")
        print("  Per-bank (weekly):")
        for bank, stats in sorted(checkpoint.per_bank.items()):
            print(
                f"    {bank}: "
                f"spend={_fmt_amount(-stats.spend)} "
                f"income={_fmt_amount(stats.income)} "
                f"net={_fmt_amount(stats.net)} "
                f"transfers={_fmt_amount(stats.transfer_total)}"
            )
        print("  Top transactions:")
        for txn in checkpoint.top_transactions:
            print(
                f"    {txn.transaction_date.isoformat()} | "
                f"{txn.source_bank} | {_fmt_amount(txn.signed_amount)} | "
                f"{txn.description[:60]}"
            )
        print("-" * 52)

    print("Month Total")
    print(f"  Spend:      {_fmt_amount(-consolidation.total_spend)}")
    print(f"  Income:     {_fmt_amount(consolidation.total_income)}")
    print(f"  Net:        {_fmt_amount(consolidation.total_net)}")
    print(f"  Transfers:  {_fmt_amount(consolidation.transfer_total)}")


if __name__ == '__main__':
    main()
