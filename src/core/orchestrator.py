import logging
import shutil
from pathlib import Path

import pandas as pd

from src.core.deduplicator import deduplicate, get_seen_hashes_from_file, save_seen_hashes_to_file
from src.core.ingestion import discover_files
from src.core.transfer_detector import detect_transfers
from src.exporters.goodbudget import export_to_goodbudget
from src.exporters.report import generate_report
from src.models.result import ProcessingResult
from src.models.transactions import Transaction
from src.parsers.axis import AxisParser
from src.parsers.base import BankParser
from src.parsers.hdfc import HDFCParser
from src.parsers.sbi import SBIParser

logger = logging.getLogger("fipro.orchestrator")


def process_pipeline(config: dict) -> list[ProcessingResult]:
    results: list[ProcessingResult] = []
    input_path = config["paths"]["input"]
    output_path = config["paths"].get("output", "data/output")
    processed_path = config["paths"].get("processed", "data/processed")
    failed_path = config["paths"].get("failed", "data/failed")

    seen_hashes_path = Path("data/.seen_hashes")
    seen_hashes = get_seen_hashes_from_file(str(seen_hashes_path))

    files = discover_files(config)
    if not files:
        logger.info("No files found in %s", input_path)
        return results

    parsers = [HDFCParser(), SBIParser(), AxisParser()]
    all_transactions: list[Transaction] = []

    for crawled in files:
        try:
            df = load_statement_dataframe(crawled.filepath)
            parser = route_file_to_parser(crawled.filename, df, parsers)
            txns = parser.extract_transactions(df, crawled.filepath)
            all_transactions.extend(txns)
            move_file_to_processed(crawled.filepath, processed_path)
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
            results.append(
                ProcessingResult(
                    source_file=crawled.filepath,
                    bank=crawled.metadata.get("bank", "UNKNOWN"),
                    total_transactions=0,
                    successful=0,
                    failed=0,
                    duplicates_skipped=0,
                    transactions=[],
                    errors=[str(e)],
                    warnings=[],
                )
            )

    # consolidation
    all_transactions, dups = deduplicate(all_transactions, seen_hashes)
    if not config.get("processing", {}).get("skip_internal_transfers", False):
        all_transactions = detect_transfers(all_transactions)
    save_seen_hashes_to_file(seen_hashes, str(seen_hashes_path))

    # export
    csv_path = f"{output_path}/goodbudget_export.csv"
    export_to_goodbudget(all_transactions, csv_path, config)
    report_path = f"{output_path}/processing_report.json"
    generate_report(results, report_path)
    logger.info("Pipeline complete. %d transactions exported to %s", len(all_transactions), csv_path)
    return results


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
    dst = dest / Path(source_path).name
    shutil.move(source_path, dst)
    return str(dst)


def move_file_to_failed(source_path: str, dest_dir: str, error: str) -> str:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    dst = dest / Path(source_path).name
    shutil.move(source_path, dst)
    error_log = dest / f"{Path(source_path).stem}.error.txt"
    error_log.write_text(error)
    return str(dst)
