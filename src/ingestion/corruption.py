from __future__ import annotations

import pandas as pd


import json
import random
import pandas as pd
from datetime import timedelta

def _log_entry(c_type, param, before, after, affected_ids):
    return {
        "type": c_type,
        "parameter": param,
        "before_count": before,
        "after_count": after,
        "affected_record_ids": list(affected_ids)
    }

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhiều dạng data corruption có chủ đích trên dữ liệu sạch."""
    if df.empty:
        return df

    corrupted_df = df.copy()
    corruption_log = []
    
    # Helper để lấy paper_id từ index
    def get_ids(idx):
        return corrupted_df.loc[idx, 'paper_id'].tolist() if 'paper_id' in corrupted_df.columns else list(idx)

    # 1. Drop một số latest records (5%)
    before = len(corrupted_df)
    drop_count = max(1, int(before * 0.05))
    if 'published_dt' in corrupted_df.columns:
        corrupted_df = corrupted_df.sort_values('published_dt', ascending=False)
        dropped_indices = corrupted_df.index[:drop_count]
        dropped_ids = get_ids(dropped_indices)
        corrupted_df = corrupted_df.drop(dropped_indices)
    else:
        dropped_indices = corrupted_df.index[:drop_count]
        dropped_ids = get_ids(dropped_indices)
        corrupted_df = corrupted_df.iloc[drop_count:]
    corruption_log.append(_log_entry("drop_latest", "5%", before, len(corrupted_df), dropped_ids))

    # 2. Blank summary (5%)
    before = len(corrupted_df)
    blank_idx = corrupted_df.sample(frac=0.05).index
    blank_ids = get_ids(blank_idx)
    corrupted_df.loc[blank_idx, 'summary'] = ""
    corruption_log.append(_log_entry("blank_summary", "5%", before, len(corrupted_df), blank_ids))

    # 3. Inject noise vào text (5%)
    before = len(corrupted_df)
    noise_idx = corrupted_df.sample(frac=0.05).index
    noise_ids = get_ids(noise_idx)
    corrupted_df.loc[noise_idx, 'summary'] = corrupted_df.loc[noise_idx, 'summary'].astype(str) + " [NOISE]"
    corruption_log.append(_log_entry("inject_noise", "5% '[NOISE]'", before, len(corrupted_df), noise_ids))

    # 4. Truncate title (5%)
    before = len(corrupted_df)
    trunc_idx = corrupted_df.sample(frac=0.05).index
    trunc_ids = get_ids(trunc_idx)
    corrupted_df.loc[trunc_idx, 'title'] = corrupted_df.loc[trunc_idx, 'title'].astype(str).str[:10] + "..."
    corruption_log.append(_log_entry("truncate_title", "10 chars", before, len(corrupted_df), trunc_ids))

    # 5. Stale published date (5% - lùi 2 năm)
    before = len(corrupted_df)
    if 'published_dt' in corrupted_df.columns:
        corrupted_df['published_dt'] = pd.to_datetime(corrupted_df['published_dt'], errors='coerce')
        stale_idx = corrupted_df.sample(frac=0.05).index
        stale_ids = get_ids(stale_idx)
        corrupted_df.loc[stale_idx, 'published_dt'] = corrupted_df.loc[stale_idx, 'published_dt'] - pd.Timedelta(days=730)
        if 'published' in corrupted_df.columns:
            corrupted_df.loc[stale_idx, 'published'] = corrupted_df.loc[stale_idx, 'published_dt'].dt.strftime('%Y-%m-%d')
        corruption_log.append(_log_entry("stale_date", "-2 years", before, len(corrupted_df), stale_ids))

    # 6. Add duplicates (5%)
    before = len(corrupted_df)
    dup_rows = corrupted_df.sample(frac=0.05)
    dup_ids = dup_rows['paper_id'].tolist() if 'paper_id' in dup_rows.columns else dup_rows.index.tolist()
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
    corruption_log.append(_log_entry("add_duplicates", "5%", before, len(corrupted_df), dup_ids))

    # 7. Rebuild `text_for_embedding`
    corrupted_df['text_for_embedding'] = (
        "Title: " + corrupted_df['title'].astype(str) + "\n" +
        "Authors: " + corrupted_df.get('authors_joined', '').astype(str) + "\n" +
        "Categories: " + corrupted_df.get('categories_joined', '').astype(str) + "\n" +
        "Summary: " + corrupted_df['summary'].astype(str)
    )

    # 8. Ghi log
    try:
        import os
        os.makedirs(os.path.dirname(output_log_path), exist_ok=True)
        with open(output_log_path, 'w', encoding='utf-8') as f:
            json.dump(corruption_log, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Lỗi khi ghi log: {e}")

    return corrupted_df
