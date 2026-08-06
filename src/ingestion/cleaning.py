from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord


import logging

logger = logging.getLogger(__name__)

def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records thành dataframe sẵn sàng để embed."""
    if not records:
        logger.warning("No records provided to clean.")
        return pd.DataFrame()

    df = pd.DataFrame([vars(r) for r in records])
    initial_count = len(df)

    # 1. Normalize title, summary, authors, categories
    # Drop records thiếu các trường cốt lõi
    df = df.dropna(subset=['paper_id', 'title', 'summary'])
    df = df[(df['title'].str.strip() != '') & (df['summary'].str.strip() != '')]
    missing_fields_count = initial_count - len(df)

    df['authors'] = df['authors'].apply(lambda x: x if isinstance(x, list) else [])
    df['categories'] = df['categories'].apply(lambda x: x if isinstance(x, list) else [])
    
    df['authors_joined'] = df['authors'].apply(lambda x: ", ".join(x) if x else "Unknown")
    df['categories_joined'] = df['categories'].apply(lambda x: ", ".join(x) if x else "Unknown")
    df['summary_chars'] = df['summary'].apply(lambda x: len(str(x)))

    # Parse published/updated date
    df['published_dt'] = pd.to_datetime(df['published'], errors='coerce')
    df['updated_dt'] = pd.to_datetime(df['updated'], errors='coerce').fillna(df['published_dt'])

    # 2. Dedupe theo stable ID (paper_id)
    before_dedupe = len(df)
    # Ưu tiên bản ghi cập nhật mới nhất
    df = df.sort_values('updated_dt', ascending=False).drop_duplicates(subset=['paper_id'], keep='first')
    dedupe_count = before_dedupe - len(df)

    # Tính age_days
    run_date_naive = run_date.replace(tzinfo=None)
    df['age_days'] = (run_date_naive - df['published_dt'].dt.tz_localize(None)).dt.days
    df['age_days'] = df['age_days'].fillna(0).astype(int)

    # Build text_for_embedding
    df['text_for_embedding'] = (
        "Title: " + df['title'].astype(str) + "\n" +
        "Authors: " + df['authors_joined'] + "\n" +
        "Categories: " + df['categories_joined'] + "\n" +
        "Summary: " + df['summary'].astype(str)
    )

    # 3. Log/count lý do filter hoặc dedupe
    logger.info("--- BÁO CÁO KẾT QUẢ DATA CLEANING ---")
    logger.info("Tổng số bản ghi ban đầu: %s", initial_count)
    logger.info("Bị loại bỏ do thiếu title/summary: %s", missing_fields_count)
    logger.info("Bị loại bỏ do trùng lặp (duplicate): %s", dedupe_count)
    logger.info("Tổng số bản ghi còn lại (Cleaned): %s", len(df))

    return df.reset_index(drop=True)
