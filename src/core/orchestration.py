from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


REQUIRED_CLEAN_COLUMNS = frozenset(
    {
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "categories_joined",
        "age_days",
        "text_for_embedding",
        "abs_url",
        "pdf_url",
    }
)


def require_artifacts(paths: Iterable[Path], stage: str) -> None:
    """Fail early with one actionable error when a pipeline input is missing."""
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        formatted = "\n- ".join(missing)
        raise FileNotFoundError(
            f"Cannot run {stage}; required artifacts are missing:\n- {formatted}"
        )


def validate_clean_dataframe(df: pd.DataFrame, stage: str) -> None:
    """Validate the cross-module clean-data contract before indexing."""
    if df.empty:
        raise ValueError(f"{stage} produced an empty clean dataset.")

    missing_columns = sorted(REQUIRED_CLEAN_COLUMNS.difference(df.columns))
    if missing_columns:
        raise ValueError(
            f"{stage} violates the clean-data contract; missing columns: "
            f"{', '.join(missing_columns)}"
        )

    paper_ids = df["paper_id"]
    if paper_ids.isna().any() or paper_ids.astype(str).str.strip().eq("").any():
        raise ValueError(f"{stage} contains null or blank paper_id values.")
    if paper_ids.astype(str).duplicated().any():
        raise ValueError(f"{stage} contains duplicate paper_id values.")

    embedding_text = df["text_for_embedding"]
    if embedding_text.isna().any() or embedding_text.astype(str).str.strip().eq("").any():
        raise ValueError(f"{stage} contains blank text_for_embedding values.")


def dataframe_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a dataframe to JSON-safe records using pandas' serializer."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def load_clean_csv(path: Path, stage: str) -> pd.DataFrame:
    require_artifacts([path], stage)
    df = pd.read_csv(path)
    validate_clean_dataframe(df, stage)
    return df
