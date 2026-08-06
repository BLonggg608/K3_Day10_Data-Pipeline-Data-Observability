from __future__ import annotations

from typing import Any

import pandas as pd

from core.orchestration import validate_clean_dataframe
from core.utils import first_sentence, write_json


QUESTION_BUILDERS = (
    (
        "summary",
        lambda row: f"What is the paper '{row['title']}' about?",
        lambda row: first_sentence(str(row["summary"])),
    ),
    (
        "authors",
        lambda row: f"Who authored the paper '{row['title']}'?",
        lambda row: str(row["authors_joined"]),
    ),
    (
        "date",
        lambda row: f"When was the paper '{row['title']}' published?",
        lambda row: str(row["published"]),
    ),
    (
        "categories",
        lambda row: f"What categories does the paper '{row['title']}' have?",
        lambda row: str(row["categories_joined"]),
    ),
)


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build a deterministic, source-grounded evaluation set from clean data."""
    validate_clean_dataframe(df, "evaluation test-set input")
    if len(df) < 4:
        raise ValueError("At least four clean documents are required to build the evaluation set.")

    # Sorting makes the same clean snapshot produce the same test set on every run.
    selected = df.sort_values("paper_id").head(min(6, len(df)))
    test_set: list[dict[str, Any]] = []
    for document_number, (_, row) in enumerate(selected.iterrows(), start=1):
        paper_id = str(row["paper_id"])
        for question_type, build_question, build_answer in QUESTION_BUILDERS:
            answer = build_answer(row).strip()
            if not answer:
                continue
            test_set.append(
                {
                    "id": f"q-{document_number:02d}-{question_type}",
                    "question_type": question_type,
                    "question": build_question(row),
                    "ground_truth": answer,
                    "ground_truth_doc_ids": [paper_id],
                }
            )

    if not test_set:
        raise ValueError("No valid evaluation questions could be generated from clean data.")
    write_json(output_path, test_set)
    return test_set
