from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.config import Settings, load_settings
from core.orchestration import dataframe_records, validate_clean_dataframe
from core.utils import write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


def _load_or_fetch_records(settings: Settings):
    raw_snapshot = settings.paths.raw_records_json
    if raw_snapshot.is_file() and not settings.refresh_source:
        return load_raw_records(raw_snapshot), "saved raw snapshot"
    return fetch_source_records(settings), "Crossref API"


def _artifact_path(settings: Settings, path) -> str:
    """Render portable artifact paths in generated reports."""
    try:
        return path.resolve().relative_to(settings.paths.project_dir).as_posix()
    except ValueError:
        return str(path)


def run_phase1(settings: Settings | None = None) -> dict[str, Any]:
    """Run the reproducible baseline pipeline and return its artifact summary."""
    settings = settings or load_settings()
    records, source_mode = _load_or_fetch_records(settings)
    if not records:
        raise ValueError("Crossref ingestion returned no usable records.")

    clean_df = build_clean_dataframe(records, run_date=datetime.now(UTC))
    validate_clean_dataframe(clean_df, "baseline cleaning")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, dataframe_records(clean_df))

    index = LocalEmbeddingIndex.build(
        clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )

    if settings.refresh_test_set or not settings.paths.eval_testset.is_file():
        build_test_set(clean_df, settings.paths.eval_testset)

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    quality = run_data_quality_checks(clean_df, settings, report_name="baseline")
    freshness = build_freshness_report(
        clean_df,
        settings,
        report_path=settings.paths.freshness_report,
    )

    source_summary = {
        "source": settings.source_api,
        "mode": source_mode,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "requested_records": settings.max_results,
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "raw_api_response": _artifact_path(settings, settings.paths.raw_api_response),
        "raw_records_json": _artifact_path(settings, settings.paths.raw_records_json),
    }
    generate_phase1_report(
        settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation.summary,
        quality=quality,
        freshness=freshness,
    )

    return {
        "source": source_summary,
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
        "report": str(settings.paths.baseline_report),
    }


def main() -> None:
    result = run_phase1()
    print(f"Baseline pipeline completed: {result['report']}")
