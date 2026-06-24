import logging
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from src.core.deduplicator import get_seen_hashes_from_file, save_seen_hashes_to_file
from src.core.external_account_detector import detect_external_account_payments
from src.core.ingestion import discover_files
from src.core.pipeline_lifecycle import (
    move_file_to_failed as _move_file_to_failed,
)
from src.core.pipeline_lifecycle import (
    move_file_to_processed as _move_file_to_processed,
)
from src.core.pipeline_lifecycle import (
    move_processed_files,
    persist_failed_files,
)
from src.core.transaction_consolidation import apply_processing_metrics, consolidate_transactions
from src.exporters.goodbudget import export_to_goodbudget
from src.exporters.hub_csv import export_hub_csv
from src.exporters.report import generate_report
from src.models.result import HubSummary, PipelineRun, ProcessingResult
from src.models.transactions import Transaction
from src.parsers.axis import AxisParser
from src.parsers.base import BankParser
from src.parsers.hdfc import HDFCParser
from src.parsers.sbi import SBIParser
from src.utils.report_helpers import include_internal_transfers_from_config

logger = logging.getLogger("fipro.orchestrator")

_EXPORT_ARTIFACTS = (
    "goodbudget_export.csv",
    "hub_summary.csv",
    "processing_report.json",
)


def _commit_export_artifacts(staging_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in _EXPORT_ARTIFACTS:
        shutil.copy2(staging_dir / name, output_dir / name)


def _run_export_phase(
    config: dict,
    export_transactions: list[Transaction],
    results: list[ProcessingResult],
    deduplicated_transactions: list[Transaction],
    duplicates_skipped: int,
    output_path: str,
) -> tuple[str, str, str, HubSummary]:
    """
    Write exports to a staging directory, then publish all artifacts together.

    On failure before commit, nothing is written to the final output directory.
    """
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".fipro_export_", dir=output_dir) as staging_name:
        staging_dir = Path(staging_name)
        csv_staging = staging_dir / "goodbudget_export.csv"
        hub_staging = staging_dir / "hub_summary.csv"
        report_staging = staging_dir / "processing_report.json"

        export_to_goodbudget(export_transactions, str(csv_staging), config)
        export_hub_csv(export_transactions, str(hub_staging))
        _, hub_summary = generate_report(
            results,
            str(report_staging),
            config=config,
            duplicates_skipped=duplicates_skipped,
            transactions=deduplicated_transactions,
        )
        _commit_export_artifacts(staging_dir, output_dir)

    return (
        str(output_dir / "goodbudget_export.csv"),
        str(output_dir / "hub_summary.csv"),
        str(output_dir / "processing_report.json"),
        hub_summary,
    )


def process_pipeline(config: dict) -> PipelineRun:
    results: list[ProcessingResult] = []
    input_path = config["paths"]["input"]
    output_path = config["paths"].get("output", "data/output")
    processed_path = config["paths"].get("processed", "data/processed")
    failed_path = config["paths"].get("failed", "data/failed")
    fail_on_file_error = config.get("processing", {}).get("fail_on_file_error", False)
    processing_config = config.get("processing", {})
    seen_hashes_path = Path(processing_config.get("seen_hashes_path", "data/.seen_hashes"))
    seen_hashes = get_seen_hashes_from_file(str(seen_hashes_path))
    prior_seen_hashes = set(seen_hashes)

    files = discover_files(config)
    if not files:
        logger.info("No files found in %s", input_path)
        return PipelineRun(
            results=[],
            deduplicated_transactions=[],
            goodbudget_csv_path="",
            report_json_path="",
            hub_csv_path="",
            hub_summary=HubSummary.empty(),
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
            error = str(e)
            logger.error("Failed processing %s: %s", crawled.filepath, error)
            failures.append((crawled.filepath, error))
            results.append(
                ProcessingResult(
                    source_file=crawled.filepath,
                    bank=crawled.metadata.get("bank", "UNKNOWN"),
                    total_transactions=0,
                    successful=0,
                    failed=1,
                    duplicates_skipped=0,
                    transactions=[],
                    errors=[error],
                    warnings=[],
                )
            )

    if failures:
        persist_failed_files(failures, failed_path, mover=move_file_to_failed)

    if failures and fail_on_file_error:
        raise RuntimeError(f"Processing aborted because {len(failures)} file(s) failed to parse")

    consolidation = consolidate_transactions(
        all_transactions,
        seen_hashes=seen_hashes,
        prior_seen_hashes=prior_seen_hashes,
        include_internal_transfers=include_internal_transfers_from_config(config),
    )
    detect_external_account_payments(consolidation.deduplicated_transactions, config)
    deduplicated_transactions = consolidation.deduplicated_transactions
    export_transactions = consolidation.export_transactions
    apply_processing_metrics(
        results,
        duplicates_by_source=consolidation.duplicates_by_source,
        transactions_by_source=consolidation.transactions_by_source,
    )
    duplicates_skipped = sum(consolidation.duplicates_by_source.values())

    csv_path, hub_path, report_path, hub_summary = _run_export_phase(
        config,
        export_transactions,
        results,
        deduplicated_transactions,
        duplicates_skipped,
        output_path,
    )

    save_seen_hashes_to_file(seen_hashes, str(seen_hashes_path))

    move_processed_files(processed_files, processed_path, mover=move_file_to_processed)

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
    return _move_file_to_processed(source_path, dest_dir)


def move_file_to_failed(source_path: str, dest_dir: str, error: str) -> str:
    return _move_file_to_failed(source_path, dest_dir, error)
