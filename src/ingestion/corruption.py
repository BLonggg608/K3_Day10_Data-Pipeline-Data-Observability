from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def _target_indices(df: pd.DataFrame, count: int, offset: int) -> list[int]:
    """Select deterministic, non-overlapping records by stable paper_id order."""
    ordered = df.sort_values("paper_id").index.tolist()
    if not ordered:
        return []
    start = min(offset, len(ordered) - 1)
    return ordered[start : start + count]


def _log_entry(kind: str, df: pd.DataFrame, indices: list[int], **parameters: Any) -> dict[str, Any]:
    return {
        "type": kind,
        "count": len(indices),
        "paper_ids": [str(value) for value in df.loc[indices, "paper_id"].tolist()],
        "parameters": parameters,
    }


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: str | Path) -> pd.DataFrame:
    """Create deterministic, traceable corruption scenarios on clean data."""
    if df.empty:
        raise ValueError("Cannot corrupt an empty clean dataframe.")

    required = {
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "categories_joined",
        "age_days",
    }
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(f"Corruption input is missing columns: {', '.join(missing)}")

    corrupted = df.copy(deep=True)
    corrupted["published_dt"] = pd.to_datetime(corrupted["published"], errors="coerce")
    affected_count = max(1, round(len(corrupted) * 0.05))
    log_entries: list[dict[str, Any]] = []

    # Drop the newest records while retaining their IDs in the log for lineage.
    latest_indices = (
        corrupted.sort_values("published_dt", ascending=False, na_position="last")
        .head(affected_count)
        .index.tolist()
    )
    log_entries.append(_log_entry("drop_latest_records", corrupted, latest_indices))
    corrupted = corrupted.drop(index=latest_indices)

    # Stable paper_id ordering keeps every rerun reproducible. Separate offsets
    # avoid accidentally applying every corruption to the same record.
    blank_indices = _target_indices(corrupted, affected_count, 0)
    log_entries.append(_log_entry("blank_summary", corrupted, blank_indices))
    corrupted.loc[blank_indices, "summary"] = ""

    noise_indices = _target_indices(corrupted, affected_count, affected_count)
    log_entries.append(
        _log_entry(
            "inject_summary_noise",
            corrupted,
            noise_indices,
            suffix="[NOISE_INJECTED_XYZ_123]",
        )
    )
    corrupted.loc[noise_indices, "summary"] = (
        corrupted.loc[noise_indices, "summary"].astype(str)
        + " [NOISE_INJECTED_XYZ_123]"
    )

    title_indices = _target_indices(corrupted, affected_count, affected_count * 2)
    log_entries.append(
        _log_entry("truncate_title", corrupted, title_indices, retained_characters=10)
    )
    corrupted.loc[title_indices, "title"] = (
        corrupted.loc[title_indices, "title"].astype(str).str[:10] + "..."
    )

    stale_indices = _target_indices(corrupted, affected_count, affected_count * 3)
    log_entries.append(
        _log_entry("stale_publication_date", corrupted, stale_indices, days_shifted=730)
    )
    shifted_dates = corrupted.loc[stale_indices, "published_dt"] - pd.Timedelta(days=730)
    corrupted.loc[stale_indices, "published_dt"] = shifted_dates
    corrupted.loc[stale_indices, "published"] = shifted_dates.dt.strftime("%Y-%m-%d")
    corrupted.loc[stale_indices, "age_days"] = (
        pd.to_numeric(corrupted.loc[stale_indices, "age_days"], errors="coerce").fillna(0)
        + 730
    ).astype(int)

    duplicate_indices = _target_indices(corrupted, affected_count, affected_count * 4)
    log_entries.append(_log_entry("add_duplicate_rows", corrupted, duplicate_indices))
    duplicate_rows = corrupted.loc[duplicate_indices].copy()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)

    corrupted["text_for_embedding"] = (
        "Title: " + corrupted["title"].fillna("").astype(str) + "\n"
        "Authors: " + corrupted["authors_joined"].fillna("").astype(str) + "\n"
        "Categories: " + corrupted["categories_joined"].fillna("").astype(str) + "\n"
        "Summary: " + corrupted["summary"].fillna("").astype(str)
    )
    corrupted = corrupted.reset_index(drop=True)

    write_json(
        Path(output_log_path),
        {
            "strategy": "deterministic paper_id ordering",
            "input_rows": int(len(df)),
            "output_rows": int(len(corrupted)),
            "corruptions": log_entries,
        },
    )
    return corrupted
