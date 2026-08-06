from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from core.config import Settings, load_settings
from core.orchestration import (
    dataframe_records,
    load_clean_csv,
    require_artifacts,
    validate_clean_dataframe,
)
from core.utils import read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def _evaluate_state(
    df,
    settings: Settings,
    *,
    state: str,
    embeddings_path,
    metrics_path,
    answers_path,
    freshness_path,
) -> dict[str, Any]:
    index = LocalEmbeddingIndex.build(
        df,
        settings=settings,
        embeddings_output_path=embeddings_path,
    )
    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=metrics_path,
        answers_output_path=answers_path,
    )
    quality = run_data_quality_checks(df, settings, report_name=state)
    freshness = build_freshness_report(df, settings, report_path=freshness_path)
    return {
        "metrics": evaluation.summary,
        "quality": quality,
        "freshness": freshness,
    }


def run_corruption_flow(settings: Settings | None = None) -> dict[str, Any]:
    """Evaluate corruption impact, repair from raw, and create a fair comparison."""
    settings = settings or load_settings()
    require_artifacts(
        [
            settings.paths.clean_csv,
            settings.paths.raw_records_json,
            settings.paths.eval_testset,
            settings.paths.baseline_metrics,
        ],
        stage="corruption flow",
    )

    baseline_df = load_clean_csv(settings.paths.clean_csv, "baseline artifact")
    baseline_metrics = read_json(settings.paths.baseline_metrics)
    baseline_quality_path = settings.paths.quality_dir / "baseline_quality_report.json"
    require_artifacts(
        [baseline_quality_path, settings.paths.freshness_report],
        stage="corruption comparison",
    )
    baseline_quality = read_json(baseline_quality_path)
    baseline_freshness = read_json(settings.paths.freshness_report)

    corrupted_df = corrupt_clean_dataframe(
        baseline_df.copy(deep=True),
        settings.paths.corruption_log,
    )
    if corrupted_df.empty:
        raise ValueError("Corruption removed every row; the dataset cannot be evaluated.")
    # Corruption intentionally violates quality constraints such as uniqueness or
    # completeness, so only require the columns needed by the downstream index.
    required_index_columns = {
        "paper_id",
        "title",
        "published",
        "authors_joined",
        "categories_joined",
        "summary",
        "text_for_embedding",
        "abs_url",
        "pdf_url",
    }
    missing = sorted(required_index_columns.difference(corrupted_df.columns))
    if missing:
        raise ValueError(f"Corrupted dataset is missing index columns: {', '.join(missing)}")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, dataframe_records(corrupted_df))
    corrupted = _evaluate_state(
        corrupted_df,
        settings,
        state="corrupted",
        embeddings_path=settings.paths.corrupted_embeddings_json,
        metrics_path=settings.paths.corrupted_metrics,
        answers_path=settings.paths.corrupted_answers,
        freshness_path=settings.paths.corrupted_freshness_report,
    )

    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, run_date=datetime.now(UTC))
    validate_clean_dataframe(repaired_df, "repair from raw snapshot")
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, dataframe_records(repaired_df))
    repaired = _evaluate_state(
        repaired_df,
        settings,
        state="repaired",
        embeddings_path=settings.paths.repaired_embeddings_json,
        metrics_path=settings.paths.repaired_metrics,
        answers_path=settings.paths.repaired_answers,
        freshness_path=settings.paths.repaired_freshness_report,
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted["metrics"],
        repaired_metrics=repaired["metrics"],
        corrupted_quality=corrupted["quality"],
        repaired_quality=repaired["quality"],
        corrupted_freshness=corrupted["freshness"],
        repaired_freshness=repaired["freshness"],
        baseline_quality=baseline_quality,
        baseline_freshness=baseline_freshness,
    )

    return {
        "baseline_metrics": baseline_metrics,
        "corrupted": corrupted,
        "repaired": repaired,
        "report": str(settings.paths.comparison_report),
    }


def main() -> None:
    result = run_corruption_flow()
    print(f"Corruption flow completed: {result['report']}")
