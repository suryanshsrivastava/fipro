"""Main processing orchestrator for Fipro."""

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd

from src.core.deduplicator import deduplicate
from src.core.ingestion import discover_files, get_bank_from_filename
from src.core.transfer_detector import detect_transfers
from src.exporters.goodbudget import export_to_goodbudget
from src.exporters.hub_csv import export_hub_csv
from src.exporters.report import build_hub_summary, generate_report
from src.models.account import CrawledFile
from src.models.result import PipelineRun, ProcessingResult
from src.models.transactions import Transaction
from src.utils.report_helpers import filter_transactions_for_export
from src.parsers.axis import AxisParser
from src.parsers.hdfc import HDFCParser
from src.parsers.sbi import SBIParser


AVAILABLE_PARSERS = [HDFCParser(), SBIParser(), AxisParser()]


def process_pipeline(config: dict) -> PipelineRun:
    """Execute the file-based processing pipeline."""
    files = discover_files(config)
    if not files:
        return PipelineRun(
            results=[],
            deduplicated_transactions=[],
            goodbudget_csv_path="",
            report_json_path="",
            hub_csv_path="",
            hub_summary={
                "date_range": {"earliest": None, "latest": None},
                "cash_flow": None,
                "net_worth_proxy": {
                    "total_across_statements": None,
                    "reason_if_no_total": "no_input_files",
                },
            },
        )

    fail_on_file_error = config.get("processing", {}).get("fail_on_file_error", True)
    results: List[ProcessingResult] = []
    all_transactions: List[Transaction] = []
    failures: list[tuple[CrawledFile, str]] = []
    successful_files: list[CrawledFile] = []

    for crawled_file in files:
        bank_hint = crawled_file.metadata.get(
            "bank", get_bank_from_filename(crawled_file.filename)
        )
        result = ProcessingResult(
            source_file=crawled_file.filepath,
            bank=bank_hint,
            total_transactions=0,
            successful=0,
            failed=0,
            duplicates_skipped=0,
            transactions=[],
            errors=[],
            warnings=[],
        )
        try:
            parser = route_file_to_parser(crawled_file.filepath, AVAILABLE_PARSERS)
            transactions = parse_file(crawled_file.filepath, parser)
            result.bank = parser.bank_name
            result.total_transactions = len(transactions)
            result.successful = len(transactions)
            result.transactions = transactions
            all_transactions.extend(transactions)
            successful_files.append(crawled_file)
        except Exception as exc:
            result.errors.append(str(exc))
            result.failed = 1
            failures.append((crawled_file, str(exc)))
        results.append(result)

    failed_dir = config["paths"]["failed"]
    for crawled_file, error in failures:
        move_file_to_failed(crawled_file.filepath, failed_dir, error)

    if failures and fail_on_file_error:
        raise RuntimeError(
            f"Processing aborted because {len(failures)} file(s) failed to parse"
        )

    deduplicated_transactions, _ = deduplicate(all_transactions)
    duplicates_by_source = _count_duplicates_by_source(all_transactions)
    deduplicated_transactions = detect_transfers(deduplicated_transactions)

    transactions_by_source: dict[str, list[Transaction]] = {}
    for transaction in deduplicated_transactions:
        transactions_by_source.setdefault(transaction.source_file, []).append(transaction)

    for result in results:
        result.duplicates_skipped = duplicates_by_source.get(result.source_file, 0)
        result.transactions = transactions_by_source.get(result.source_file, [])
        result.successful = len(result.transactions)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = Path(config["paths"]["output"])
    csv_path = output_dir / f"goodbudget_{timestamp}.csv"
    report_path = output_dir / f"processing_report_{timestamp}.json"
    hub_path = output_dir / f"hub_summary_{timestamp}.csv"

    exported_count = export_to_goodbudget(
        deduplicated_transactions, str(csv_path), config
    )
    include_internal = config.get("processing", {}).get(
        "include_internal_transfers", True
    )
    hub_transactions = filter_transactions_for_export(
        deduplicated_transactions, include_internal
    )
    export_hub_csv(hub_transactions, str(hub_path))

    report = generate_report(
        results,
        str(report_path),
        exported_transactions=exported_count,
        config=config,
    )
    hub_summary = build_hub_summary(report)

    processed_dir = config["paths"]["processed"]
    for crawled_file in successful_files:
        move_file_to_processed(crawled_file.filepath, processed_dir)

    return PipelineRun(
        results=results,
        deduplicated_transactions=deduplicated_transactions,
        goodbudget_csv_path=str(csv_path),
        report_json_path=str(report_path),
        hub_csv_path=str(hub_path),
        hub_summary=hub_summary,
    )


def route_file_to_parser(filename: str, parsers: List) -> object:
    """Route a discovered file to a parser."""
    filepath = Path(filename)
    bank_hint = get_bank_from_filename(filepath.name)

    prioritized = [
        parser for parser in parsers if parser.bank_name == bank_hint
    ] + [parser for parser in parsers if parser.bank_name != bank_hint]

    for parser in prioritized:
        try:
            df = _load_file_as_dataframe(str(filepath), parser)
            if df is not None and parser.can_parse(filepath.name, df):
                return parser
        except Exception:
            continue

    raise ValueError(f"No parser can handle file: {filepath.name}")


def parse_file(filepath: str, parser: object) -> List[Transaction]:
    """Load a file into a DataFrame and parse it into transactions."""
    dataframe = _load_file_as_dataframe(filepath, parser)
    if dataframe is None:
        raise ValueError(f"Could not load file: {filepath}")
    return parser.extract_transactions(dataframe, filepath)


def move_file_to_processed(source_path: str, dest_dir: str) -> str:
    """Move a successfully processed file into the processed directory."""
    destination_dir = Path(dest_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = _unique_destination(destination_dir / Path(source_path).name)
    shutil.move(source_path, destination)
    return str(destination)


def move_file_to_failed(source_path: str, dest_dir: str, error: str) -> str:
    """Move a failed file and write a sidecar error log."""
    destination_dir = Path(dest_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)
    destination = _unique_destination(destination_dir / Path(source_path).name)
    shutil.move(source_path, destination)
    error_path = destination.with_name(destination.name + ".error.txt")
    error_path.write_text(
        f"File: {Path(source_path).name}\nError: {error}\n", encoding="utf-8"
    )
    return str(destination)


def _load_file_as_dataframe(filepath: str, parser: object) -> pd.DataFrame | None:
    if isinstance(parser, SBIParser):
        dataframe = SBIParser.load_sbi_file(filepath)
        if dataframe is not None:
            return dataframe
        return None

    extension = Path(filepath).suffix.lower()
    engines = ["xlrd", "openpyxl"] if extension == ".xls" else ["openpyxl", "xlrd"]
    for engine in engines:
        try:
            return pd.read_excel(filepath, engine=engine, header=None)
        except Exception:
            continue
    return None


def _unique_destination(path: Path) -> Path:
    candidate = path
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        counter += 1
    return candidate


def _count_duplicates_by_source(transactions: List[Transaction]) -> dict[str, int]:
    duplicates_by_source: dict[str, int] = {}
    seen_hashes: set[str] = set()
    for transaction in transactions:
        if transaction.hash in seen_hashes:
            duplicates_by_source[transaction.source_file] = (
                duplicates_by_source.get(transaction.source_file, 0) + 1
            )
            continue
        seen_hashes.add(transaction.hash)
    return duplicates_by_source
