import logging
import shutil
import tempfile
from pathlib import Path

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
from src.utils.report_helpers import include_internal_transfers_from_config

logger = logging.getLogger("fipro.orchestrator")

GOODBUDGET_CSV = "goodbudget_export.csv"
DASHBOARD_CSV = "dashboard_data.csv"
HUB_CSV = "hub_summary.csv"
REPORT_JSON = "processing_report.json"
_EXPORT_ARTIFACTS = (GOODBUDGET_CSV, DASHBOARD_CSV, HUB_CSV, REPORT_JSON)


def _run_export_phase(
    config: dict,
    consolidation: ConsolidationResult,
    results: list[ProcessingResult],
    output_dir: Path,
) -> HubSummary:
    """
    Write exports to a staging directory, then publish all artifacts to ``output_dir`` together.

    On failure before commit, nothing is written to the final output directory.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".fipro_export_", dir=output_dir) as staging_name:
        staging_dir = Path(staging_name)
        export_to_goodbudget(consolidation.export_transactions, str(staging_dir / GOODBUDGET_CSV), config)
        export_dashboard_data(consolidation.deduplicated_transactions, str(staging_dir / DASHBOARD_CSV))
        export_hub_csv(consolidation.export_transactions, str(staging_dir / HUB_CSV))
        _, hub_summary = generate_report(
            results,
            str(staging_dir / REPORT_JSON),
            config=config,
            duplicates_skipped=consolidation.duplicates_skipped,
            transactions=consolidation.deduplicated_transactions,
            export_transactions=consolidation.export_transactions,
        )
        for name in _EXPORT_ARTIFACTS:
            shutil.copy2(staging_dir / name, output_dir / name)

    return hub_summary


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
        return PipelineRun.without_exports("no_input_files")

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
        return PipelineRun.without_exports(
            "no_files_processed", results=extraction.results, locked_files=extraction.locked_files
        )

    consolidation = consolidate_transactions(
        extraction.all_transactions,
        seen_hashes=seen_hashes,
        include_internal_transfers=include_internal_transfers_from_config(config),
    )
    detect_external_account_payments(consolidation.deduplicated_transactions, config)
    apply_processing_metrics(extraction.results, consolidation)

    output_dir = Path(output_path)
    hub_summary = _run_export_phase(config, consolidation, extraction.results, output_dir)

    # Hashes are recorded only after the statements were archived, so a failed move can't leave
    # a still-pending file whose transactions would all be skipped as duplicates on the next run.
    move_processed_files(extraction.processed_files, processed_path)
    save_seen_hashes_to_file(seen_hashes, str(seen_hashes_path))

    logger.info("Pipeline complete. %d transactions exported to %s", consolidation.exported_count, output_dir)
    return PipelineRun(
        results=extraction.results,
        deduplicated_transactions=consolidation.deduplicated_transactions,
        export_transactions=consolidation.export_transactions,
        exported_count=consolidation.exported_count,
        goodbudget_csv_path=str(output_dir / GOODBUDGET_CSV),
        report_json_path=str(output_dir / REPORT_JSON),
        hub_csv_path=str(output_dir / HUB_CSV),
        dashboard_csv_path=str(output_dir / DASHBOARD_CSV),
        hub_summary=hub_summary,
        locked_files=extraction.locked_files,
    )
