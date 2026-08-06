# Checkpoint 6 — Rà soát release

- Trạng thái: **SẴN SÀNG RELEASE**
- Kết quả kiểm tra: **22/22 PASS**
- Test-set SHA-256: `90D8ED972B2DBBB84C35E22FB8E0DFE9B775839433A05065B2242C7836083139`

## Evidence theo 5 vai trò

1. **Điều phối pipeline:** ba trạng thái dùng path/collection riêng; release checks và artifact hashes được lưu trong `data/results/checkpoint6_release_check.json`.
2. **Ingestion:** raw snapshot có 24 records và là nguồn để chạy lại cleaning; không refresh Crossref trong repair.
3. **Cleaning & corruption:** repaired clean khớp baseline clean; corruption log có 6 entry truy vết record bị tác động.
4. **RAG & agent:** `papers-baseline`, `papers-corrupted`, `papers-repaired` đều có 24 documents.
5. **Evaluation & observability:** cùng 24 câu hỏi; quality chuyển PASS → FAIL → PASS và freshness chuyển FRESH → STALE → FRESH.

## So sánh metrics

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 |
| `mean_token_f1` | 1.0000 | 0.8414 | 1.0000 |
| `judge_accuracy` | 0.9583 | 0.7917 | 0.9583 |
| `mean_judge_score` | 4.8333 | 4.2500 | 4.8333 |

## Các kiểm tra trước release

| Check | Trạng thái | Chi tiết |
| --- | --- | --- |
| raw_snapshot_available | PASS | `{"records": 24}` |
| repair_matches_baseline_clean | PASS | `{"baseline_rows": 24, "repaired_rows": 24}` |
| corruption_changes_clean_data | PASS | `{"baseline_rows": 24, "corrupted_rows": 24}` |
| test_set_hash_locked | PASS | `{"expected": "90D8ED972B2DBBB84C35E22FB8E0DFE9B775839433A05065B2242C7836083139", "actual": "90D8ED972B2DBBB84C35E22FB8E0DFE9B775839433A05065B2242C7836083139"}` |
| baseline_evaluation_contract | PASS | `{"answers": 24, "samples": 24}` |
| corrupted_evaluation_contract | PASS | `{"answers": 24, "samples": 24}` |
| repaired_evaluation_contract | PASS | `{"answers": 24, "samples": 24}` |
| repaired_same_query_smoke | PASS | `{"question_id": "q-01-authors", "answer_recovered": true, "retrieval_recovered": true}` |
| corruption_degrades_agent_metric | PASS | `{"retrieval_hit_rate": 0.0, "mean_token_f1": -0.15860215053763438, "judge_accuracy": -0.16666666666666674, "mean_judge_score": -0.583333333333333}` |
| repair_recovers_agent_metrics | PASS | `{"retrieval_hit_rate": 0.0, "mean_token_f1": 0.0, "judge_accuracy": 0.0, "mean_judge_score": 0.0}` |
| evaluator_no_fallback | PASS | `{"baseline": "llm", "corrupted": "llm", "repaired": "llm"}` |
| quality_transition | PASS | `{"baseline": true, "corrupted": false, "repaired": true}` |
| freshness_transition | PASS | `{"baseline": true, "corrupted": false, "repaired": true}` |
| baseline_collection | PASS | `{"name": "papers-baseline", "chroma_documents": 24, "manifest_documents": 24, "persist_path": "data/chroma"}` |
| corrupted_collection | PASS | `{"name": "papers-corrupted", "chroma_documents": 24, "manifest_documents": 24, "persist_path": "data/chroma"}` |
| repaired_collection | PASS | `{"name": "papers-repaired", "chroma_documents": 24, "manifest_documents": 24, "persist_path": "data/chroma"}` |
| corruption_log_traceable | PASS | `{"entries": 6}` |
| repair_restores_affected_records | PASS | `{"affected_records": 6, "restored_records": 6}` |
| env_not_tracked | PASS | `{"tracked": false}` |
| no_tracked_secret_pattern | PASS | `{"locations": []}` |
| no_student_todo_or_merge_marker | PASS | `{"locations": []}` |
| portable_report_paths | PASS | `{"report": "data/reports/phase1_report.md"}` |

## Warning đã được audit

- phase1_report.md thay đổi sau khi baseline được khóa ở CP4 vì report đã được Việt hóa và các lineage path đã được chuyển thành path portable; metrics, answers, quality và freshness đã khóa vẫn không thay đổi.

## Kết luận

Corruption làm giảm answer metrics trong khi `retrieval_hit_rate` vẫn giữ nguyên; quality và freshness phát hiện duplicate, summary rỗng và record stale. Repair từ raw snapshot khôi phục clean dataset, quality/freshness và toàn bộ metrics về baseline. Ragas không được bật nên không có kết luận dựa trên Ragas.
