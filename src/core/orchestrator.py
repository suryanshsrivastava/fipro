import logging
import shutil
from pathlib import Path

import pandas as pd

from src.core.deduplicator import deduplicate, get_seen_hashes_from_file, save_seen_hashes_to_file
from src.core.ingestion import discover_files
from src.core.transfer_detector import detect_transfers
from src.exporters.goodbudget import export_to_goodbudget
from src.exporters.hub_csv import export_hub_csv
from src.exporters.report import build_hub_summary, generate_report
from src.models.result import PipelineRun, ProcessingResult
from src.models.transactions import Transaction, TransactionStatus
from src.utils.report_helpers import filter_transactions_for_export
from src.parsers.axis import AxisParser
from src.parsers.base import BankParser
from src.parsers.hdfc import HDFCParser
from src.parsers.sbi import SBIParser

logger = logging.getLogger("fipro.orchestrator")

_EMPTY_HUB_SUMMARY = {
    "date_range": {"earliest": None, "latest": None},
    "cash_flow": None,
    "net_worth_proxy": {
        "total_across_statements": None,
        "reason_if_no_total": "no_input_files",
    },
}


def process_pipeline(config: dict) -> PipelineRun:
    results: list[ProcessingResult] = []
    input_path = config["paths"]["input"]
    output_path = config["paths"].get("output", "data/output")
    processed_path = config["paths"].get("processed", "data/processed")
    failed_path = config["paths"].get("failed", "data/failed")
    fail_on_file_error = config.get("processing", {}).get("fail_on_file_error", False)

    seen_hashes_path = Path("data/.seen_hashes")
    seen_hashes = get_seen_hashes_from_file(str(seen_hashes_path))

    files = discover_files(config)
    if not files:
        logger.info("No files found in %s", input_path)
        return PipelineRun(
            results=[],
            deduplicated_transactions=[],
            goodbudget_csv_path="",
            report_json_path="",
            hub_csv_path="",
            hub_summary=_EMPTY_HUB_SUMMARY,
        )

    parsers = [HDFCParser(), SBIParser(), AxisParser()]
    all_transactions: list[Transaction] = []
    processed_files: list[str] = []
    failures: list[tuple[str, str]] = []

    for crawled in files:
        try:
            df = load_statement_dataframe(crawled.filepath)
            parser = route_file_to_parser(crawled.filename, df, parsers)
            txns = parser.extract_transactions(df, crawled.filepath)
            all_transactions.extend(txns)
            processed_files.append(crawled.filepath)
            results.append(
                ProcessingResult(
                    source_file=crawled.filepath,
                    bank=parser.bank_name,
                    total_transactions=len(txns),
                    successful=len(txns),
                    failed=0,
                    duplicates_skipped=0,
                    transactions=txns,
                    errors=[],
                    warnings=[],
                )
            )
        except Exception as e:
            logger.error("Failed processing %s: %s", crawled.filepath, e)
            move_file_to_failed(crawled.filepath, failed_path, str(e))
            failures.append((crawled.filepath, str(e)))
            results.append(
                ProcessingResult(
                    source_file=crawled.filepath,
                    bank=crawled.metadata.get("bank", "UNKNOWN"),
                    total_transactions=0,
                    successful=0,
                    failed=1,
                    duplicates_skipped=0,
                    transactions=[],
                    errors=[str(e)],
                    warnings=[],
                )
            )

    if failures and fail_on_file_error:
        raise RuntimeError(f"Processing aborted because {len(failures)} file(s) failed to parse")

    deduplicated_transactions, dups = deduplicate(all_transactions, seen_hashes)
    deduplicated_transactions = detect_transfers(deduplicated_transactions)
    duplicates_by_source = _count_duplicates_by_source(all_transactions)

    transactions_by_source: dict[str, list[Transaction]] = {}
    for transaction in deduplicated_transactions:
        transactions_by_source.setdefault(transaction.source_file, []).append(transaction)

    for result in results:
        result.duplicates_skipped = duplicates_by_source.get(result.source_file, 0)
        result.transactions = transactions_by_source.get(result.source_file, [])
        result.successful = len(result.transactions)

    skip_internal = config.get("processing", {}).get("skip_internal_transfers", False)
    include_internal = config.get("processing", {}).get("include_internal_transfers", not skip_internal)
    export_transactions = filter_transactions_for_export(deduplicated_transactions, include_internal)

    csv_path = f"{output_path}/goodbudget_export.csv"
    export_to_goodbudget(export_transactions, csv_path, config)
    save_seen_hashes_to_file(seen_hashes, str(seen_hashes_path))

    hub_path = f"{output_path}/hub_summary.csv"
    export_hub_csv(export_transactions, hub_path)

    report_path = f"{output_path}/processing_report.json"
    report = generate_report(
        results,
        report_path,
        exported_transactions=len(export_transactions),
        config=config,
        duplicates_skipped=dups,
    )
    hub_summary = build_hub_summary(report)

    for filepath in processed_files:
        move_file_to_processed(filepath, processed_path)

    logger.info("Pipeline complete. %d transactions exported to %s", len(export_transactions), csv_path)
    return PipelineRun(
        results=results,
        deduplicated_transactions=deduplicated_transactions,
        goodbudget_csv_path=csv_path,
        report_json_path=report_path,
        hub_csv_path=hub_path,
        hub_summary=hub_summary,
    )


def extract_raw_transactions(filepaths: list[str]) -> list[Transaction]:
    parsers = [HDFCParser(), SBIParser(), AxisParser()]
    transactions: list[Transaction] = []
    for filepath in sorted(filepaths):
        df = load_statement_dataframe(filepath)
        parser = route_file_to_parser(Path(filepath).name, df, parsers)
        transactions.extend(parser.extract_transactions(df, filepath))
    return transactions


def extract_raw_dataframe(filepaths: list[str]) -> pd.DataFrame:
    transactions = extract_raw_transactions(filepaths)
    records = [
        {
            "transaction_date": t.transaction_date,
            "description": t.description,
            "amount": t.amount,
            "transaction_type": t.transaction_type.value,
            "source_bank": t.source_bank,
            "source_file": t.source_file,
            "balance": t.balance,
        }
        for t in transactions
    ]
    return pd.DataFrame.from_records(records)


def load_statement_dataframe(filepath: str) -> pd.DataFrame:
    path = Path(filepath)
    suffix = path.suffix.lower()
    if "sbi" in path.name.lower():
        df = SBIParser.load_sbi_file(filepath)
        if df is None:
            raise ValueError(f"Unable to load SBI statement: {filepath}")
        return df
    if suffix not in {".xls", ".xlsx"}:
        raise ValueError(f"Unsupported format: {filepath}")
    engine = "xlrd" if suffix == ".xls" else "openpyxl"
    return pd.read_excel(filepath, engine=engine, header=None)


def route_file_to_parser(filename: str, df: pd.DataFrame, parsers: list[BankParser]) -> BankParser:
    for parser in parsers:
        if parser.can_parse(filename, df):
            return parser
    raise ValueError(f"No parser available for {filename}")


def move_file_to_processed(source_path: str, dest_dir: str) -> str:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    dst = _unique_destination(dest / Path(source_path).name)
    shutil.move(source_path, dst)
    return str(dst)


def move_file_to_failed(source_path: str, dest_dir: str, error: str) -> str:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    dst = _unique_destination(dest / Path(source_path).name)
    shutil.move(source_path, dst)
    error_log = dst.with_name(dst.name + ".error.txt")
    error_log.write_text(error)
    return str(dst)


def _unique_destination(path: Path) -> Path:
    candidate = path
    counter = 1
    while candidate.exists():
        candidate = path.with_name(f"{path.stem}_{counter}{path.suffix}")
        counter += 1
    return candidate


def _count_duplicates_by_source(transactions: list[Transaction]) -> dict[str, int]:
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
