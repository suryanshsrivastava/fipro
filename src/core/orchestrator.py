import logging
import shutil
import tempfile
from pathlib import Path

import pandas as pd

from src.core.deduplicator import get_seen_hashes_from_file, save_seen_hashes_to_file
from src.core.external_account_detector import detect_external_account_payments
from src.core.ingestion import discover_files
from src.core.parser_registry import get_default_parser_registry
from src.core.pipeline_lifecycle import move_processed_files, persist_failed_files
from src.core.statement_extraction import extract_from_crawled_files
from src.core.transaction_consolidation import ConsolidationResult, apply_processing_metrics, consolidate_transactions
from src.exporters.goodbudget import export_dashboard_data, export_to_goodbudget
from src.exporters.hub_csv import export_hub_csv
from src.exporters.report import generate_report
from src.models.result import HubSummary, PipelineRun, ProcessingResult
from src.models.transactions import Transaction
from src.utils.report_helpers import include_internal_transfers_from_config

logger = logging.getLogger("fipro.orchestrator")

_EXPORT_ARTIFACTS = (
    "goodbudget_export.csv",
    "dashboard_data.csv",
    "hub_summary.csv",
    "processing_report.json",
)


def _commit_export_artifacts(staging_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name in _EXPORT_ARTIFACTS:
        shutil.copy2(staging_dir / name, output_dir / name)


def _run_export_phase(
    config: dict,
    consolidation: ConsolidationResult,
    results: list[ProcessingResult],
    output_path: str,
) -> tuple[str, str, str, str, HubSummary]:
    """
    Write exports to a staging directory, then publish all artifacts together.

    On failure before commit, nothing is written to the final output directory.
    """
    export_transactions = consolidation.export_transactions
    deduplicated_transactions = consolidation.deduplicated_transactions
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".fipro_export_", dir=output_dir) as staging_name:
        staging_dir = Path(staging_name)
        csv_staging = staging_dir / "goodbudget_export.csv"
        dashboard_staging = staging_dir / "dashboard_data.csv"
        hub_staging = staging_dir / "hub_summary.csv"
        report_staging = staging_dir / "processing_report.json"

        export_to_goodbudget(export_transactions, str(csv_staging), config)
        export_dashboard_data(deduplicated_transactions, str(dashboard_staging))
        export_hub_csv(export_transactions, str(hub_staging))
        _, hub_summary = generate_report(
            results,
            str(report_staging),
            config=config,
            duplicates_skipped=consolidation.duplicates_skipped,
            transactions=deduplicated_transactions,
            export_transactions=export_transactions,
            exported_transactions=consolidation.exported_count,
        )
        _commit_export_artifacts(staging_dir, output_dir)

    return (
        str(output_dir / "goodbudget_export.csv"),
        str(output_dir / "hub_summary.csv"),
        str(output_dir / "processing_report.json"),
        str(output_dir / "dashboard_data.csv"),
        hub_summary,
    )


def process_pipeline(config: dict, passwords: dict[str, str] | None = None) -> PipelineRun:
    """Run the full pipeline. ``passwords`` maps bank (e.g. "SBI") to a statement password for this run only."""
    input_path = config["paths"]["input"]
    output_path = config["paths"].get("output", "data/output")
    processed_path = config["paths"].get("processed", "data/processed")
    failed_path = config["paths"].get("failed", "data/failed")
    fail_on_file_error = config.get("processing", {}).get("fail_on_file_error", False)
    processing_config = config.get("processing", {})
    seen_hashes_path = Path(processing_config.get("seen_hashes_path", "data/.seen_hashes"))
    seen_hashes = get_seen_hashes_from_file(str(seen_hashes_path))

    files = discover_files(config)
    if not files:
        logger.info("No files found in %s", input_path)
        return PipelineRun(
            results=[],
            deduplicated_transactions=[],
            export_transactions=[],
            exported_count=0,
            goodbudget_csv_path="",
            report_json_path="",
            hub_csv_path="",
            dashboard_csv_path="",
            hub_summary=HubSummary.empty(),
        )

    extraction = extract_from_crawled_files(
        files,
        parser_registry=get_default_parser_registry(),
        input_path=input_path,
        passwords=passwords,
    )

    if extraction.failures:
        persist_failed_files(extraction.failures, failed_path)

    if extraction.failures and fail_on_file_error:
        raise RuntimeError(f"Processing aborted because {len(extraction.failures)} file(s) failed to parse")

    if not extraction.processed_files:
        # Nothing parsed (all locked or failed): keep the previous exports instead of overwriting them with empty files.
        logger.info("No statements were processed; leaving existing exports in %s untouched", output_path)
        return PipelineRun(
            results=extraction.results,
            deduplicated_transactions=[],
            export_transactions=[],
            exported_count=0,
            goodbudget_csv_path="",
            report_json_path="",
            hub_csv_path="",
            dashboard_csv_path="",
            hub_summary=HubSummary.empty("no_files_processed"),
            locked_files=extraction.locked_files,
        )

    consolidation = consolidate_transactions(
        extraction.all_transactions,
        seen_hashes=seen_hashes,
        include_internal_transfers=include_internal_transfers_from_config(config),
    )
    detect_external_account_payments(consolidation.deduplicated_transactions, config)
    apply_processing_metrics(extraction.results, consolidation)

    csv_path, hub_path, report_path, dashboard_path, hub_summary = _run_export_phase(
        config,
        consolidation,
        extraction.results,
        output_path,
    )

    save_seen_hashes_to_file(seen_hashes, str(seen_hashes_path))

    move_processed_files(extraction.processed_files, processed_path)

    logger.info("Pipeline complete. %d transactions exported to %s", consolidation.exported_count, csv_path)
    return PipelineRun(
        results=extraction.results,
        deduplicated_transactions=consolidation.deduplicated_transactions,
        export_transactions=consolidation.export_transactions,
        exported_count=consolidation.exported_count,
        goodbudget_csv_path=csv_path,
        report_json_path=report_path,
        hub_csv_path=hub_path,
        dashboard_csv_path=dashboard_path,
        hub_summary=hub_summary,
        locked_files=extraction.locked_files,
    )


def extract_raw_transactions(filepaths: list[str]) -> list[Transaction]:
    registry = get_default_parser_registry()
    transactions: list[Transaction] = []
    for filepath in sorted(filepaths):
        transactions.extend(registry.extract_transactions(filepath).transactions)
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
