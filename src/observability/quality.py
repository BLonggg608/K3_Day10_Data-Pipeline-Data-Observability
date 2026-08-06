from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def _check(name: str, dimension: str, success: bool, observed: Any, expectation: str) -> dict[str, Any]:
    return {
        "name": name,
        "dimension": dimension,
        "success": bool(success),
        "observed": observed,
        "expectation": expectation,
    }


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run auditable quality checks and persist their observed values."""
    required = {"paper_id", "title", "summary", "age_days", "text_for_embedding"}
    missing_columns = sorted(required.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Quality input is missing columns: {', '.join(missing_columns)}")

    paper_ids = df["paper_id"].fillna("").astype(str).str.strip()
    titles = df["title"].fillna("").astype(str).str.strip()
    summaries = df["summary"].fillna("").astype(str).str.strip()
    embedding_text = df["text_for_embedding"].fillna("").astype(str).str.strip()
    age_days = pd.to_numeric(df["age_days"], errors="coerce")

    checks = [
        _check("row_count", "completeness", len(df) > 0, int(len(df)), "> 0"),
        _check("paper_id_not_blank", "completeness", paper_ids.ne("").all(), int(paper_ids.eq("").sum()), "0 blank"),
        _check("paper_id_unique", "uniqueness", not paper_ids.duplicated().any(), int(paper_ids.duplicated().sum()), "0 duplicates"),
        _check("title_not_blank", "completeness", titles.ne("").all(), int(titles.eq("").sum()), "0 blank"),
        _check("summary_not_blank", "completeness", summaries.ne("").all(), int(summaries.eq("").sum()), "0 blank"),
        _check("embedding_text_not_blank", "completeness", embedding_text.ne("").all(), int(embedding_text.eq("").sum()), "0 blank"),
        _check("age_days_valid", "validity", age_days.notna().all() and age_days.ge(0).all(), int((age_days.isna() | age_days.lt(0)).sum()), "0 invalid"),
        _check(
            "records_within_freshness_threshold",
            "freshness",
            age_days.notna().all() and age_days.le(settings.freshness_threshold_days).all(),
            int(age_days.gt(settings.freshness_threshold_days).sum()),
            f"0 records older than {settings.freshness_threshold_days} days",
        ),
    ]
    payload = {
        "report_name": report_name,
        "total_rows": int(len(df)),
        "passed_checks": sum(1 for item in checks if item["success"]),
        "failed_checks": sum(1 for item in checks if not item["success"]),
        "success": all(item["success"] for item in checks),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}_quality_report.json", payload)
    return payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Summarize publication freshness from persisted clean-data fields."""
    required = {"published", "age_days"}
    missing_columns = sorted(required.difference(df.columns))
    if missing_columns:
        raise ValueError(f"Freshness input is missing columns: {', '.join(missing_columns)}")

    published = pd.to_datetime(df["published"], errors="coerce")
    age_days = pd.to_numeric(df["age_days"], errors="coerce")
    stale_mask = age_days.gt(settings.freshness_threshold_days)
    invalid_dates = int(published.isna().sum())
    payload = {
        "latest_published": published.max().date().isoformat() if published.notna().any() else None,
        "oldest_published": published.min().date().isoformat() if published.notna().any() else None,
        "freshness_threshold_days": settings.freshness_threshold_days,
        "stale_rows": int(stale_mask.sum()),
        "invalid_date_rows": invalid_dates,
        "total_rows": int(len(df)),
        "is_fresh": bool(len(df) > 0 and stale_mask.sum() == 0 and invalid_dates == 0),
    }
    write_json(report_path, payload)
    return payload
