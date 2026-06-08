import json
from pathlib import Path

from src.models.result import ProcessingResult


def generate_report(results: list[ProcessingResult], output_path: str, duplicates_skipped: int = 0) -> dict:
    report = {
        "total_files": len(results),
        "total_transactions": sum(r.total_transactions for r in results),
        "successful_transactions": sum(r.successful for r in results),
        "failed_transactions": sum(r.failed for r in results),
        "duplicates_skipped": duplicates_skipped,
        "total_errors": sum(len(r.errors) for r in results),
        "files": [_result_to_dict(r) for r in results],
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    return report


def _result_to_dict(r: ProcessingResult) -> dict:
    return {
        "source_file": r.source_file,
        "bank": r.bank,
        "total_transactions": r.total_transactions,
        "successful": r.successful,
        "failed": r.failed,
        "duplicates_skipped": r.duplicates_skipped,
        "errors": r.errors,
        "warnings": r.warnings,
    }
