# Báo cáo so sánh Corruption: Baseline → Corrupted → Repaired

## Retrieval và answer metrics

| Metric | Baseline | Corrupted | Δ (Corrupted − Baseline) | Repaired | Δ (Repaired − Baseline) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | +0.0000 | 1.0000 | +0.0000 |
| `mean_token_f1` | 1.0000 | 0.8414 | -0.1586 | 1.0000 | +0.0000 |
| `judge_accuracy` | 0.9583 | 0.7917 | -0.1667 | 0.9583 | +0.0000 |
| `mean_judge_score` | 4.8333 | 4.2500 | -0.5833 | 4.8333 | +0.0000 |

- Corrupted samples: 24
- Repaired samples: 24

## Data quality

### Corrupted

- Overall status: **FAIL**
- Passed checks: 5
- Failed checks: 3

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
| Row count | Completeness | PASS | 24 |
| paper_id không rỗng | Completeness | PASS | 0 |
| paper_id duy nhất | Uniqueness | FAIL | 1 |
| title không rỗng | Completeness | PASS | 0 |
| summary không rỗng | Completeness | FAIL | 1 |
| embedding text không rỗng | Completeness | PASS | 0 |
| age_days hợp lệ | Validity | PASS | 0 |
| Records nằm trong freshness threshold | Freshness | FAIL | 1 |

### Repaired

- Overall status: **PASS**
- Passed checks: 8
- Failed checks: 0

| Check | Dimension | Status | Observed |
| --- | --- | --- | ---: |
| Row count | Completeness | PASS | 24 |
| paper_id không rỗng | Completeness | PASS | 0 |
| paper_id duy nhất | Uniqueness | PASS | 0 |
| title không rỗng | Completeness | PASS | 0 |
| summary không rỗng | Completeness | PASS | 0 |
| embedding text không rỗng | Completeness | PASS | 0 |
| age_days hợp lệ | Validity | PASS | 0 |
| Records nằm trong freshness threshold | Freshness | PASS | 0 |


## Freshness

### Corrupted

| Field | Value |
| --- | --- |
| Latest published | 2026-07-13 |
| Oldest published | 2024-02-13 |
| Freshness threshold (days) | 180 |
| Stale rows | 1 |
| Invalid date rows | 0 |
| Status | STALE/INVALID |

### Repaired

| Field | Value |
| --- | --- |
| Latest published | 2026-08-01 |
| Oldest published | 2026-02-12 |
| Freshness threshold (days) | 180 |
| Stale rows | 0 |
| Invalid date rows | 0 |
| Status | FRESH |


## Evidence boundary

Báo cáo này được tạo hoàn toàn từ metrics, quality checks và freshness report thật của ba trạng thái baseline/corrupted/repaired; không có số liệu nào bị chỉnh sửa thủ công. Nếu repaired chưa khôi phục hoàn toàn về mức baseline, delta ở trên sẽ vẫn khác 0 và cần được nêu rõ khi demo thay vì tô hồng kết quả.
