# Báo cáo so sánh corruption: Baseline → Corrupted → Repaired

## Retrieval và answer metrics

| Metric | Baseline | Corrupted | Δ (Corrupted − Baseline) | Repaired | Δ (Repaired − Baseline) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | +0.0000 | 1.0000 | +0.0000 |
| `mean_token_f1` | 1.0000 | 0.8414 | -0.1586 | 1.0000 | +0.0000 |
| `judge_accuracy` | 0.9583 | 0.7917 | -0.1667 | 0.9583 | +0.0000 |
| `mean_judge_score` | 4.8333 | 4.2500 | -0.5833 | 4.8333 | +0.0000 |

- Số sample corrupted: 24
- Số sample repaired: 24

## Data quality

### Baseline

- Trạng thái tổng thể: **PASS**
- Số check đạt: 8
- Số check không đạt: 0

| Check | Dimension | Trạng thái | Giá trị quan sát |
| --- | --- | --- | ---: |
| Số lượng row | Completeness | PASS | 24 |
| paper_id không rỗng | Completeness | PASS | 0 |
| paper_id duy nhất | Uniqueness | PASS | 0 |
| title không rỗng | Completeness | PASS | 0 |
| summary không rỗng | Completeness | PASS | 0 |
| embedding text không rỗng | Completeness | PASS | 0 |
| age_days hợp lệ | Validity | PASS | 0 |
| Record nằm trong freshness threshold | Freshness | PASS | 0 |

### Corrupted

- Trạng thái tổng thể: **FAIL**
- Số check đạt: 5
- Số check không đạt: 3

| Check | Dimension | Trạng thái | Giá trị quan sát |
| --- | --- | --- | ---: |
| Số lượng row | Completeness | PASS | 24 |
| paper_id không rỗng | Completeness | PASS | 0 |
| paper_id duy nhất | Uniqueness | FAIL | 1 |
| title không rỗng | Completeness | PASS | 0 |
| summary không rỗng | Completeness | FAIL | 1 |
| embedding text không rỗng | Completeness | PASS | 0 |
| age_days hợp lệ | Validity | PASS | 0 |
| Record nằm trong freshness threshold | Freshness | FAIL | 1 |

### Repaired

- Trạng thái tổng thể: **PASS**
- Số check đạt: 8
- Số check không đạt: 0

| Check | Dimension | Trạng thái | Giá trị quan sát |
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

### Baseline

| Field | Giá trị |
| --- | --- |
| Ngày published mới nhất | 2026-08-01 |
| Ngày published cũ nhất | 2026-02-12 |
| Freshness threshold (ngày) | 180 |
| Số row stale | 0 |
| Số row có date không hợp lệ | 0 |
| Trạng thái | FRESH |

### Corrupted

| Field | Giá trị |
| --- | --- |
| Ngày published mới nhất | 2026-07-13 |
| Ngày published cũ nhất | 2024-02-13 |
| Freshness threshold (ngày) | 180 |
| Số row stale | 1 |
| Số row có date không hợp lệ | 0 |
| Trạng thái | STALE/INVALID |

### Repaired

| Field | Giá trị |
| --- | --- |
| Ngày published mới nhất | 2026-08-01 |
| Ngày published cũ nhất | 2026-02-12 |
| Freshness threshold (ngày) | 180 |
| Số row stale | 0 |
| Số row có date không hợp lệ | 0 |
| Trạng thái | FRESH |


## Phạm vi của bằng chứng

Báo cáo này được tạo hoàn toàn từ metrics, quality checks và freshness report thật của ba trạng thái baseline/corrupted/repaired; không có số liệu nào bị chỉnh sửa thủ công. Nếu repaired chưa khôi phục hoàn toàn về mức baseline, delta ở trên sẽ vẫn khác 0 và cần được nêu rõ khi demo thay vì tô hồng kết quả.
