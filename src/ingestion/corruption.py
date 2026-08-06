from __future__ import annotations

import pandas as pd


import json
import random
import pandas as pd
from datetime import timedelta

def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path) -> pd.DataFrame:
    """Simulate nhiều dạng data corruption có chủ đích trên dữ liệu sạch."""
    if df.empty:
        return df

    corrupted_df = df.copy()
    corruption_log = {}
    
    # 1. Drop một số latest records (xóa 5% bài báo mới nhất)
    # Giả định có cột 'published_dt' hoặc lấy theo index nếu đã sort
    drop_count = max(1, int(len(corrupted_df) * 0.05))
    if 'published_dt' in corrupted_df.columns:
        corrupted_df = corrupted_df.sort_values('published_dt', ascending=False)
        dropped_indices = corrupted_df.index[:drop_count]
        corrupted_df = corrupted_df.drop(dropped_indices)
    else:
        # Dự phòng nếu không có published_dt
        corrupted_df = corrupted_df.iloc[drop_count:]
    corruption_log['dropped_latest_records'] = drop_count

    # 2. Blank summary ở một số dòng (5% số dòng)
    blank_idx = corrupted_df.sample(frac=0.05).index
    corrupted_df.loc[blank_idx, 'summary'] = ""
    corruption_log['blanked_summaries'] = len(blank_idx)

    # 3. Inject noise vào text (thêm ký tự lạ vào summary của 5% số dòng)
    noise_idx = corrupted_df.sample(frac=0.05).index
    corrupted_df.loc[noise_idx, 'summary'] = corrupted_df.loc[noise_idx, 'summary'].astype(str) + " [NOISE_INJECTED_XYZ_123]"
    corruption_log['injected_noise_summaries'] = len(noise_idx)

    # 4. Làm title bị truncate (cắt cụt còn 10 ký tự ở 5% số dòng)
    trunc_idx = corrupted_df.sample(frac=0.05).index
    corrupted_df.loc[trunc_idx, 'title'] = corrupted_df.loc[trunc_idx, 'title'].astype(str).str[:10] + "..."
    corruption_log['truncated_titles'] = len(trunc_idx)

    # 5. Làm published date cũ đi (lùi 2 năm với 5% số dòng)
    if 'published_dt' in corrupted_df.columns:
        stale_idx = corrupted_df.sample(frac=0.05).index
        corrupted_df.loc[stale_idx, 'published_dt'] = corrupted_df.loc[stale_idx, 'published_dt'] - pd.Timedelta(days=730)
        # Nếu đang lưu dưới dạng string thì cập nhật lại string
        if 'published' in corrupted_df.columns:
            corrupted_df.loc[stale_idx, 'published'] = corrupted_df.loc[stale_idx, 'published_dt'].dt.strftime('%Y-%m-%d')
        corruption_log['stale_published_dates'] = len(stale_idx)

    # 6. Add duplicate rows (nhân bản 5% số dòng)
    dup_rows = corrupted_df.sample(frac=0.05)
    corrupted_df = pd.concat([corrupted_df, dup_rows], ignore_index=True)
    corruption_log['added_duplicates'] = len(dup_rows)

    # 7. Rebuild `text_for_embedding` (để phản ánh các thay đổi làm hỏng data)
    corrupted_df['text_for_embedding'] = (
        "Title: " + corrupted_df['title'].astype(str) + "\n" +
        "Authors: " + corrupted_df.get('authors_joined', '').astype(str) + "\n" +
        "Categories: " + corrupted_df.get('categories_joined', '').astype(str) + "\n" +
        "Summary: " + corrupted_df['summary'].astype(str)
    )

    # 8. Ghi corruption log vào output_log_path
    try:
        import os
        os.makedirs(os.path.dirname(output_log_path), exist_ok=True)
        with open(output_log_path, 'w', encoding='utf-8') as f:
            json.dump(corruption_log, f, indent=4)
    except Exception as e:
        print(f"Lỗi khi ghi log: {e}")

    return corrupted_df
