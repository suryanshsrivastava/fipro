"""CLI entry point for Fipro."""

import argparse
import sys
from collections import defaultdict

from src.config import load_config, resolve_config_path
from src.core.ingestion import discover_files
from src.core.orchestrator import process_pipeline
from src.utils.logger import setup_logging


def main():
    """Parse CLI arguments and dispatch commands."""
    parser = argparse.ArgumentParser(prog="fipro")
    parser.add_argument(
        "--version",
        action="version",
        version="fipro 0.1.0",
    )
    subparsers = parser.add_subparsers(dest="command")

    process_parser = subparsers.add_parser("process", help="Process statement files")
    process_parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to TOML config (defaults to the project config)",
    )

    status_parser = subparsers.add_parser("status", help="Show pending input files")
    status_parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Path to TOML config (defaults to the project config)",
    )

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        return 1

    config = load_config(args.config)
    setup_logging(
        config["fipro"].get("log_level", "INFO"),
        config["paths"].get("log_file"),
    )

    if args.command == "process":
        return cmd_process(args, config)
    if args.command == "status":
        return cmd_status(args, config)
    return 1


def cmd_process(args, config: dict):
    """Run the full processing pipeline."""
    try:
        run = process_pipeline(config)
    except Exception as exc:
        print(f"Processing failed: {exc}", file=sys.stderr)
        return 1

    if not run.results:
        print("No input files found.")
        return 0

    transaction_count = sum(len(result.transactions) for result in run.results)
    print(
        f"Processed {len(run.results)} file(s) and exported {transaction_count} transaction(s)."
    )
    dr = run.hub_summary.get("date_range") or {}
    earliest, latest = dr.get("earliest"), dr.get("latest")
    if earliest and latest:
        print(f"Statement window: {earliest} to {latest}")
    cf = run.hub_summary.get("cash_flow") or {}
    if cf.get("net_cash_flow") is not None:
        print(f"Net cash flow (export scope): {cf['net_cash_flow']}")
    nw = (run.hub_summary.get("net_worth_proxy") or {}).get(
        "total_across_statements"
    )
    if nw is not None:
        print(f"Balances sum (statements with closing balance): {nw}")
    return 0


def cmd_status(args, config: dict):
    """Show the list of pending files in the input directory."""
    files = discover_files(config)
    config_path = resolve_config_path(getattr(args, "config", None))
    print(f"Config path: {config_path}")
    print(f"Input directory: {config['paths']['input']}")
    print(f"Pending files: {len(files)}")

    grouped_files: dict[str, list[str]] = defaultdict(list)
    for crawled_file in files:
        grouped_files[crawled_file.metadata.get("bank", "UNKNOWN")].append(
            crawled_file.filename
        )

    for bank in sorted(grouped_files):
        print(f"{bank}:")
        for filename in sorted(grouped_files[bank]):
            print(f"- {filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
