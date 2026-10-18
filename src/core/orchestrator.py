import logging
import shutil
import tempfile
from pathlib import Path

from src.config import Settings
from src.core.annotations import apply_annotations
from src.core.audit_log import write_audit_logs
from src.core.external_account_detector import detect_external_account_payments
from src.core.ingestion import discover_files
from src.core.parser_registry import get_default_parser_registry
from src.core.statement_extraction import extract_from_crawled_files
from src.core.transaction_consolidation import ConsolidationResult, apply_processing_metrics, consolidate_transactions
from src.exporters.goodbudget import export_dashboard_data, export_to_goodbudget
from src.exporters.hub_csv import export_hub_csv
from src.exporters.report import generate_report
from src.models.result import HubSummary, PipelineRun, ProcessingResult

logger = logging.getLogger("fipro.orchestrator")

GOODBUDGET_CSV = "goodbudget_export.csv"
DASHBOARD_CSV = "dashboard_data.csv"
HUB_CSV = "hub_summary.csv"
REPORT_JSON = "processing_report.json"
_EXPORT_ARTIFACTS = (GOODBUDGET_CSV, DASHBOARD_CSV, HUB_CSV, REPORT_JSON)


def _run_export_phase(
    settings: Settings,
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
        export_to_goodbudget(consolidation.export_transactions, str(staging_dir / GOODBUDGET_CSV), settings.goodbudget)
        export_dashboard_data(consolidation.deduplicated_transactions, str(staging_dir / DASHBOARD_CSV))
        export_hub_csv(consolidation.export_transactions, str(staging_dir / HUB_CSV))
        _, hub_summary = generate_report(
            results,
            str(staging_dir / REPORT_JSON),
            duplicates_skipped=consolidation.duplicates_skipped,
            transactions=consolidation.deduplicated_transactions,
            export_transactions=consolidation.export_transactions,
        )
        for name in _EXPORT_ARTIFACTS:
            shutil.copy2(staging_dir / name, output_dir / name)

    return hub_summary


def process_pipeline(settings: Settings, passwords: dict[str, str] | None = None) -> PipelineRun:
    """Run the full pipeline over every statement in ``paths.input`` and rebuild the exports.

    ``paths.input`` is the archive: statements are read and left exactly where they are, and every run
    re-exports the whole corpus. Runs are therefore idempotent, and adding a statement is just dropping
    it in the input folder and running again. ``passwords`` maps bank (e.g. "SBI") to a statement
    password for this run only. Unreadable statements stay in ``paths.input`` with their error reported
    in the run results and ``processing_report.json``.
    """
    files = discover_files(settings)
    if not files:
        logger.info("No files found in %s", settings.paths.input)
        return PipelineRun.without_exports("no_input_files")

    extraction = extract_from_crawled_files(
        files,
        parser_registry=get_default_parser_registry(),
        input_path=settings.paths.input,
        passwords=passwords,
    )

    write_audit_logs(extraction.results)

    if extraction.failures and settings.processing.fail_on_file_error:
        raise RuntimeError(f"Processing aborted because {len(extraction.failures)} file(s) failed to parse")

    if not extraction.processed_files:
        # Nothing parsed (all locked or failed): keep the previous exports instead of overwriting them with empty files.
        logger.info("No statements were processed; leaving existing exports in %s untouched", settings.paths.output)
        return PipelineRun.without_exports(
            "no_files_processed", results=extraction.results, locked_files=extraction.locked_files
        )

    consolidation = consolidate_transactions(
        extraction.all_transactions,
        include_internal_transfers=settings.processing.export_internal_transfers,
    )
    detect_external_account_payments(consolidation.deduplicated_transactions, settings.external_accounts)
    apply_annotations(
        consolidation.deduplicated_transactions, settings.paths.annotations, settings.paths.category_rules
    )
    apply_processing_metrics(extraction.results, consolidation)

    output_dir = Path(settings.paths.output)
    hub_summary = _run_export_phase(settings, consolidation, extraction.results, output_dir)

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
