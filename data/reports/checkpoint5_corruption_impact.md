# Checkpoint 5 — Bằng chứng về tác động của corruption

## Evaluation contract

- Test set: `data/eval/test_set.json`
- SHA-256 của test set khớp với `data/results/checkpoint4_baseline_lock.json`: **CÓ**
- Số sample: 24 ở cả lần chạy baseline và corrupted
- `top_k`: 4
- Collection corrupted: `papers-corrupted`
- Số document trong manifest corrupted: 24
- Số document trong Chroma corrupted: 24

Lần chạy corrupted sử dụng test set đã khóa. Các baseline artifact không bị ghi đè.

## So sánh metrics

| Metric | Baseline | Corrupted | Delta |
| --- | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 0.0000 |
| `mean_token_f1` | 1.0000 | 0.8414 | -0.1586 |
| `judge_accuracy` | 0.9583 | 0.7917 | -0.1667 |
| `mean_judge_score` | 4.8333 | 4.2500 | -0.5833 |

`retrieval_hit_rate` không giảm, nhưng các metrics về chất lượng câu trả lời đã giảm. Một retrieval hit chỉ có nghĩa là ground-truth document xuất hiện trong top 4; điều đó không đảm bảo document đầu tiên được dùng để trả lời là chính xác.

## Kiểm tra fallback của evaluator

| Field | Baseline | Corrupted |
| --- | ---: | ---: |
| Judge mode | `llm` | `llm` |
| Số sample dùng LLM judge | 24 | 24 |
| Số sample dùng fallback judge | 0 | 0 |

Không có sample nào của evaluator âm thầm chuyển sang heuristic fallback. Ragas được bỏ qua trong cả hai lần chạy, vì vậy báo cáo không xem đây là một lần Ragas evaluation thành công.

## So sánh quality và freshness

| Signal | Baseline | Corrupted | Thay đổi? |
| --- | ---: | ---: | --- |
| Số lượng row | 24 | 24 | Không |
| `paper_id` rỗng | 0 | 0 | Không |
| Row trùng `paper_id` | 0 | 1 | Có, xấu hơn |
| Title rỗng | 0 | 0 | Không |
| Summary rỗng | 0 | 1 | Có, xấu hơn |
| Embedding text rỗng | 0 | 0 | Không |
| `age_days` không hợp lệ | 0 | 0 | Không |
| Row stale | 0 | 1 | Có, xấu hơn |
| Ngày published không hợp lệ | 0 | 0 | Không |
| Ngày published mới nhất | 2026-08-01 | 2026-07-13 | Có, cũ hơn |
| Ngày published cũ nhất | 2026-02-12 | 2024-02-13 | Có, cũ hơn |
| Quality tổng thể | PASS | FAIL | Có, xấu hơn |
| Trạng thái freshness | FRESH | STALE | Có, xấu hơn |

Số lượng row vẫn là 24 vì một record mới nhất bị xóa và một row duplicate được thêm vào. Tổng số lượng không đổi không có nghĩa là completeness và uniqueness vẫn được bảo toàn.

## Bằng chứng ở cấp độ từng case

### Case 1 — Summary rỗng trực tiếp làm hỏng câu trả lời

- Câu hỏi: `q-01-summary`
- Ground-truth paper: `10.1007/s10278-026-02086-9`
- Corruption log: `blank_summary`
- Câu trả lời baseline: không rỗng và khớp reference
- Câu trả lời corrupted: rỗng
- Token F1: `1.0 → 0.0`
- Judge score: `5 → 2`
- Retrieval hit: `true → true`

Document vẫn được retrieve, nhưng summary bị thiếu khiến câu trả lời được tạo ra không thể sử dụng.

### Case 2 — Title bị cắt làm hỏng exact lookup và thay đổi nguồn trả lời top đầu

- Các câu hỏi: `q-03-summary`, `q-03-authors`
- Ground-truth paper: `10.1111/exsy.70341`
- Corruption log: `truncate_title`, số ký tự được giữ lại: 10
- Summary Token F1: `1.0 → 0.1935`
- Summary judge score: `5 → 2`
- Authors Token F1: `1.0 → 0.0`
- Authors judge score: `5 → 1`
- Retrieval hit vẫn là `true`

Title gốc trong câu hỏi đã khóa không còn khớp với title bị cắt trong index. Ground-truth paper vẫn xuất hiện trong top 4 nên retrieval hit vẫn là `true`, nhưng một paper khác trở thành kết quả đầu tiên được dùng để trả lời.

### Case 3 — Publication date stale làm thay đổi câu trả lời factual

- Câu hỏi: `q-04-date`
- Ground-truth paper: `10.20944/preprints202602.0996.v1`
- Corruption log: `stale_publication_date`, bị lùi 730 ngày
- Câu trả lời: `2026-02-12 → 2024-02-13`
- Token F1: `1.0 → 0.0`
- Judge score: `5 → 1`
- Freshness signal: số row stale `0 → 1`

Case này liên kết date corruption đã được log với cả observability alert và một câu trả lời RAG không chính xác.

## Các signal và corruption chưa chứng minh được tác động lên RAG

- `retrieval_hit_rate` vẫn là 1.0.
- Số lượng row vẫn là 24 vì thao tác drop và duplicate triệt tiêu nhau ở mức tổng số lượng.
- Các signal về ID rỗng, title rỗng, embedding text rỗng, age không hợp lệ và date không hợp lệ không thay đổi.
- Paper bị inject noise và paper bị duplicate chưa tạo ra mức giảm được chứng minh trên các sample của test set đã khóa.
- Paper bị drop không nằm trong sáu paper được test set đã khóa lựa chọn, nên lần chạy này không chứng minh rằng việc drop paper đó làm giảm answer metrics.
- Ragas không được bật, vì vậy không đưa ra kết luận nào về Ragas metrics.

## Kết luận

Bằng chứng cho phép đưa ra kết luận trong phạm vi giới hạn: controlled corruption làm giảm completeness, uniqueness và freshness; ba loại corruption đã được log khiến bốn evaluation case đã khóa trả về câu trả lời kém hơn. Kết quả không chứng minh rằng mọi loại corruption đều làm giảm chất lượng RAG, cũng không chứng minh rằng `retrieval_hit_rate` có thể phát hiện sự suy giảm chất lượng câu trả lời.
