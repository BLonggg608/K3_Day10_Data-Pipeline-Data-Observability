# Báo cáo baseline Pha 1

## Data source và lineage

| Field | Value |
| --- | --- |
| Source | Crossref REST API |
| Load mode | Dùng raw snapshot đã lưu |
| Query | agentic retrieval augmented generation large language model |
| Filter | from-pub-date:2026-02-07,has-abstract:true |
| Raw records | 24 |
| Clean records | 24 |
| Raw response | `data/raw/crossref_response.json` |
| Artifact raw records | `data/raw/crossref_records.json` |

## Retrieval và answer metrics

| Metric | Value |
| --- | ---: |
| `retrieval_hit_rate` | 1.0000 |
| `mean_token_f1` | 1.0000 |
| `judge_accuracy` | 0.9583 |
| `mean_judge_score` | 4.8333 |

- Evaluation samples: 24
- Judge mode: llm (24 LLM samples / 0 fallback samples)
- Ragas: Đã bỏ qua (chưa bật `RUN_RAGAS=1`).

## Data quality

- Overall status: **PASS**
- Passed checks: 8
- Failed checks: 0

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
| Số lượng row | Completeness | PASS | 24 |
| paper_id không rỗng | Completeness | PASS | 0 |
| paper_id duy nhất | Uniqueness | PASS | 0 |
| title không rỗng | Completeness | PASS | 0 |
| summary không rỗng | Completeness | PASS | 0 |
| embedding text không rỗng | Completeness | PASS | 0 |
| age_days hợp lệ | Validity | PASS | 0 |
| Record nằm trong freshness threshold | Freshness | PASS | 0 |

## Freshness

| Field | Value |
| --- | --- |
| Latest published | 2026-08-01 |
| Oldest published | 2026-02-12 |
| Freshness threshold (days) | 180 |
| Stale rows | 0 |
| Invalid date rows | 0 |
| Status | FRESH |

## Evidence boundary

Báo cáo này được tạo từ metrics baseline, kết quả kiểm tra chất lượng, freshness và thông tin truy vết nguồn raw đã lưu. Ragas được ghi rõ là bỏ qua hoặc thất bại nếu chưa chạy thành công; báo cáo không coi bước bị bỏ qua là đã đạt.
