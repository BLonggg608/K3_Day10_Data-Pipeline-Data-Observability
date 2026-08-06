# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K3 |
| Tên nhóm | No Name |
| Repository | https://github.com/BLonggg608/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đào Quốc Đại | 2A202601285 | Role 1 — Pipeline integrator | `src/core/`, `src/pipelines/`, `script/`, release và demo |
| 2 | Nguyễn Quang Minh | 2A202601955 | Role 2 — Ingestion owner | `src/ingestion/crossref.py`, `data/raw/` và raw lineage |
| 3 | Đặng Trần Trung Dũng | 2A202601785 | Role 3 — Cleaning & corruption owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, clean/corrupted/repaired data |
| 4 | Trần Hà Bảo Long | 2A202601189 | Role 4 — RAG & agent owner | `src/retrieval/`, `data/embeddings/`, Chroma collections và RAG demo |
| 5 | Nguyễn Đức Trọng | 2A202601291 | Role 5 — Evaluation & observability owner | `src/evaluation/`, `src/observability/`, `data/quality/`, metrics và reports |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành pipeline end-to-end từ Crossref raw snapshot đến cleaning, MiniLM embedding, ChromaDB retrieval, RAG evaluation, data observability, controlled corruption và repair. Baseline gồm 24 paper, 24 câu hỏi evaluation, collection `papers-baseline`, answers/metrics, quality report, freshness report và phase report. Corrupted flow tạo sáu lỗi có log truy vết: drop latest record, blank summary, inject noise, truncate title, làm publication date stale và thêm duplicate row. Corruption không làm giảm `retrieval_hit_rate` vì ground-truth document vẫn nằm trong top 4, nhưng làm `mean_token_f1` giảm từ 1.0000 xuống 0.8414, `judge_accuracy` giảm từ 0.9583 xuống 0.7917 và `mean_judge_score` giảm từ 4.8333 xuống 4.2500. Quality chuyển từ PASS sang FAIL và freshness chuyển từ FRESH sang STALE. Repair được thực hiện bằng cách chạy lại cleaning từ raw snapshot, không chỉnh tay corrupted data; clean dataset, quality/freshness và toàn bộ answer metrics được phục hồi về baseline. CP6 release check đạt 22/22 checks. Giới hạn chính là corpus chỉ có 24 paper, Ragas chưa được bật và test set được sinh từ cùng corpus nên chưa đại diện cho production traffic. Nhóm bổ sung Streamlit dashboard để demo trực quan Baseline → Corrupted → Repaired và hỗ trợ OpenAI Agent bằng `gpt-4o-mini`.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API
    -> raw response + parsed PaperRecord
    -> cleaning + data modeling
    -> text_for_embedding
    -> MiniLM embeddings + ChromaDB
    -> fixed evaluation set + RAG answers
    -> quality/freshness reports
    -> controlled corruption + corruption log
    -> papers-corrupted + re-evaluation
    -> repair bằng cách clean lại raw snapshot
    -> papers-repaired + re-evaluation
    -> comparison report + Streamlit demo
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref REST payload | Fetch có retry/backoff, lưu raw trước parse, chuẩn hóa thành `PaperRecord` với stable `paper_id` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Role 2 |
| Cleaning | `list[PaperRecord]` | Normalize text/list/date, validate, dedupe, tính `age_days`, tạo `text_for_embedding` | `data/clean/papers_clean.csv`, `.json` | Role 3 |
| Embedding/index | Clean DataFrame | Embed bằng MiniLM, lưu Chroma và portable manifest | `data/embeddings/`, collections baseline/corrupted/repaired | Role 4 |
| Evaluation | Fixed test set + index | Exact lookup/semantic search, tạo answer, tính retrieval và answer metrics, LLM judge | `data/eval/`, `data/results/*answers.json`, `*metrics.json` | Role 5 |
| Observability | Clean/corrupted/repaired DataFrame | Completeness, uniqueness, validity, freshness checks và report | `data/quality/`, `data/reports/` | Role 5 |
| Corruption/repair | Baseline clean + raw snapshot | Tạo sáu corruption deterministic; repair bằng cách chạy lại cleaning từ raw | Corrupted/repaired datasets và `corruption_log.json` | Role 3 |
| Orchestration | Settings và artifacts theo contract | Điều phối phase 1, corruption flow, release check và UI demo | `src/pipelines/`, `script/`, `app.py` | Role 1 |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openai` |
| `LLM_MODEL` | `gpt-4o-mini` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Corruption selection | Deterministic theo thứ tự `paper_id`; không dùng random seed |

API key chỉ nằm trong `.env` cục bộ và `.env` không được Git track.

### Môi trường và lệnh chạy

Nhóm sử dụng Conda environment `test_vin` đã được activate, không tạo venv mới:

```cmd
set PYTHONPATH=src
python script\run_phase1.py
python script\run_corruption_flow.py
python script\run_release_check.py
```

Mở UI demo:

```cmd
set PYTHONPATH=src
python -m streamlit run app.py
```

### Kết quả tái hiện gần nhất

| Lệnh | Trạng thái | Thời điểm kiểm tra | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công, 24/24 samples | 2026-08-06 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption/repair flow | Thành công cho corrupted và repaired, mỗi trạng thái 24/24 samples | 2026-08-06 | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |
| CP6 release check | `ready_for_release`, 22/22 PASS | 2026-08-06 | `data/results/checkpoint6_release_check.json` |
| Streamlit Local QA | Render 4 tab và query cả ba collections không có exception | 2026-08-06 | `app.py`; Streamlit AppTest |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API, endpoint `https://api.crossref.org/works` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:<ngày chạy - 180 ngày>,has-abstract:true` |
| Thời điểm lấy dữ liệu | Raw snapshot hiện không lưu riêng fetch timestamp; snapshot dùng cho bài được khóa trong `data/raw/` |
| Số record nhận được | 24 parsed records |
| Retry/backoff | Tối đa 5 attempts cho lỗi 429/503 hoặc `requests.RequestException`; dùng exponential backoff 1.5, 3, 6 và 12 giây giữa các lần thử |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | `str` | Có | Stable ID, ưu tiên DOI lowercase | Loại nếu không tạo được ID hợp lệ; dedupe theo ID |
| `title` | `str` | Có | Tiêu đề paper | Normalize whitespace; record rỗng không đạt clean contract |
| `summary` | `str` | Có | Abstract/summary đã bỏ XML/JATS | Normalize whitespace; record rỗng không đạt quality gate |
| `authors` / `authors_joined` | `list[str]` / `str` | Không | Danh sách tác giả và chuỗi dùng cho index | Chuẩn hóa list; fallback chuỗi rỗng khi nguồn thiếu |
| `categories` / `categories_joined` | `list[str]` / `str` | Không | Chủ đề/category | Chuẩn hóa list; dùng `Unknown` khi phù hợp |
| `published` | ISO date string | Có | Ngày xuất bản | Parse từ Crossref `date-parts`; date lỗi bị phát hiện bởi validity/freshness check |
| `age_days` | `int` | Có | Số ngày từ ngày chạy đến publication date | Tính từ `published`; giá trị âm/không hợp lệ làm quality check FAIL |
| `text_for_embedding` | `str` | Có | Nội dung đưa vào MiniLM | Tạo lại từ title, authors, categories và summary |
| `abs_url`, `pdf_url` | `str` | Không | Lineage/link nguồn | Chuẩn hóa thành chuỗi rỗng nếu không có |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động ở baseline snapshot | Cách xác minh |
| --- | --- | ---: | --- |
| Giữ `paper_id` không rỗng và unique | Completeness, Uniqueness | 0 record lỗi | `baseline_quality_report.json` |
| Normalize và yêu cầu title/summary không rỗng | Completeness | 0 record lỗi | Quality checks `title_not_blank`, `summary_not_blank` |
| Parse publication date và tính `age_days` | Validity, Freshness | 0 record lỗi | `age_days_valid`, `freshness_report.json` |
| Dedupe theo stable ID | Uniqueness | Raw 24 → clean 24, không loại duplicate ở baseline | So sánh raw/clean count và quality report |
| Tạo `text_for_embedding` không rỗng | Completeness | 0 record lỗi | `embedding_text_not_blank` PASS |

`text_for_embedding` có cấu trúc `Title + Authors + Categories + Summary`, giúp cùng một document hỗ trợ semantic retrieval và factual answer. Document metadata giữ `paper_id` để đối chiếu với `ground_truth_doc_ids`. `age_days` được tính từ publication date thật, không hard-code freshness status.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 24 |
| `question_type` | Summary, authors, publication date và categories |
| Ground-truth document ID | Lấy từ `paper_id` của cleaned dataset và được kiểm tra tồn tại trong index |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collections | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | OpenAI / `gpt-4o-mini` |
| Judge mode | `llm`; 24 LLM judge samples, 0 fallback ở mỗi trạng thái |
| Test set dùng chung | `data/eval/test_set.json`, SHA-256 `90D8ED972B2DBBB84C35E22FB8E0DFE9B775839433A05065B2242C7836083139` |

Test set được khóa và giữ nguyên cho cả baseline, corrupted và repaired để bảo đảm fair comparison. Nếu thay câu hỏi hoặc ground truth sau corruption, thay đổi metrics có thể đến từ evaluation contract thay vì data quality. CP6 kiểm tra hash test set và xác nhận answer IDs của cả ba trạng thái khớp cùng 24 sample IDs.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | Có | Raw response và 24 parsed records |
| Cleaned dataset | `data/clean/papers_clean.csv`, `.json` | Có | 24 rows |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Collection `papers-baseline`, 24 documents |
| Evaluation set | `data/eval/test_set.json` | Có | 24 câu hỏi đã khóa hash |
| Baseline answers/metrics | `data/results/baseline_answers.json`, `baseline_metrics.json` | Có | 24 answers |
| Quality/freshness | `data/quality/baseline_quality_report.json`, `freshness_report.json` | Có | 8/8 PASS, FRESH |
| Baseline report | `data/reports/phase1_report.md` | Có | Sinh từ artifacts thật |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | Ground-truth document xuất hiện trong top 4 ở 24/24 câu hỏi |
| `mean_token_f1` | 1.0000 | Token overlap trung bình giữa answer và ground truth đạt mức tối đa trên test set |
| `judge_accuracy` | 0.9583 | LLM judge đánh giá 23/24 answers đạt tiêu chí accuracy |
| `mean_judge_score` | 4.8333/5 | Chất lượng answer trung bình cao nhưng không tuyên bố hoàn hảo |
| Ragas | N/A | `RUN_RAGAS` không được bật; không coi bước skipped là PASS |

## 8. Data quality và freshness

### Quality checks baseline

| Check | Dimension | Kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| Row count | Completeness | Có ít nhất một row | PASS, 24 rows | `baseline_quality_report.json` |
| `paper_id` không rỗng | Completeness | 0 lỗi | PASS, 0 lỗi | Cùng artifact |
| `paper_id` unique | Uniqueness | 0 duplicate | PASS, 0 duplicate | Cùng artifact |
| Title không rỗng | Completeness | 0 lỗi | PASS, 0 lỗi | Cùng artifact |
| Summary không rỗng | Completeness | 0 lỗi | PASS, 0 lỗi | Cùng artifact |
| Embedding text không rỗng | Completeness | 0 lỗi | PASS, 0 lỗi | Cùng artifact |
| `age_days` hợp lệ | Validity | 0 lỗi | PASS, 0 lỗi | Cùng artifact |
| Record trong freshness threshold | Freshness | 0 stale | PASS, 0 stale | Cùng artifact |

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Clean DataFrame và `data/quality/freshness_report.json` |
| Publication date mới nhất | 2026-08-01 |
| Publication date cũ nhất | 2026-02-12 |
| Freshness threshold | 180 ngày |
| Trạng thái baseline | FRESH |
| Lý do | 0 stale rows và 0 invalid date rows |

## 9. Corruption scenarios và repair

Mỗi loại corruption tác động một record, tương đương khoảng 5% của dataset. Record được chọn deterministic theo `paper_id` để lần chạy có thể reproduce.

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| `drop_latest_records` | Xóa paper có publication date mới nhất | 1 | Latest date cũ hơn, có thể giảm completeness | Latest published đổi 2026-08-01 → 2026-07-13; paper không thuộc locked test set nên chưa chứng minh answer metric giảm | Reload raw snapshot và clean lại |
| `blank_summary` | Đặt summary thành chuỗi rỗng | 1 | Summary completeness FAIL | `q-01-summary`: Token F1 1.0 → 0.0, judge 5 → 2 | Khôi phục summary từ raw snapshot |
| `inject_summary_noise` | Nối suffix `[NOISE_INJECTED_XYZ_123]` | 1 | Nội dung embedding/answer bị nhiễu | Có trong artifact, nhưng locked samples chưa chứng minh tác động riêng | Clean lại raw snapshot |
| `truncate_title` | Chỉ giữ 10 ký tự đầu và thêm `...` | 1 | Exact lookup theo title có thể sai | Hai case summary/authors giảm điểm dù retrieval hit vẫn true | Khôi phục title từ raw snapshot |
| `stale_publication_date` | Lùi date 730 ngày và tăng `age_days` | 1 | Freshness FAIL | Stale rows 0 → 1; answer date 2026-02-12 → 2024-02-13 | Parse lại date từ raw snapshot |
| `add_duplicate_rows` | Copy và append một row | 1 | Uniqueness FAIL | Duplicate `paper_id` rows 0 → 1; tổng row vẫn là 24 do bù cho row đã drop | Cleaning dedupe theo stable ID |

Corruption log tồn tại tại `data/results/corruption_log.json`, gồm strategy, input/output row count, type, parameters, before/after count và affected record IDs cho cả sáu corruption.

Repair không copy baseline artifact và không chỉnh tay corrupted JSON. Pipeline reload đúng `data/raw/crossref_records.json`, chạy lại `build_clean_dataframe`, validate clean contract, build collection `papers-repaired`, rồi evaluate bằng test set cũ. CP6 xác nhận repaired clean khớp baseline clean và cả 6 affected IDs được phục hồi.

## 10. So sánh Baseline, Corrupted và Repaired

| Metric/signal | Baseline | Corrupted | Repaired | Delta corrupted − baseline | Delta repaired − baseline | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | +0.0000 | +0.0000 | Top-4 hit không phát hiện answer degradation |
| `mean_token_f1` | 1.0000 | 0.8414 | 1.0000 | -0.1586 | +0.0000 | Corrupted content làm giảm token overlap; repair phục hồi hoàn toàn |
| `judge_accuracy` | 0.9583 | 0.7917 | 0.9583 | -0.1667 | +0.0000 | LLM judge phát hiện answers sai/kém hơn |
| `mean_judge_score` | 4.8333 | 4.2500 | 4.8333 | -0.5833 | +0.0000 | Answer quality giảm rồi phục hồi về baseline |
| Quality checks | 8 PASS / 0 FAIL | 5 PASS / 3 FAIL | 8 PASS / 0 FAIL | Duplicate, blank summary, stale record | Phục hồi hoàn toàn | Chuyển trạng thái PASS → FAIL → PASS |
| Freshness | FRESH, 0 stale | STALE, 1 stale | FRESH, 0 stale | Xấu hơn | Phục hồi hoàn toàn | Chuyển FRESH → STALE → FRESH |

Hai quan hệ nhân quả có bằng chứng:

1. `blank_summary` trên paper `10.1007/s10278-026-02086-9` → quality check summary FAIL → câu trả lời `q-01-summary` rỗng, Token F1 giảm 1.0 → 0.0 và judge score giảm 5 → 2, dù retrieval hit vẫn true.
2. `stale_publication_date` lùi 730 ngày → freshness phát hiện stale rows 0 → 1 → `q-04-date` trả 2024-02-13 thay vì 2026-02-12, Token F1 giảm 1.0 → 0.0 và judge score giảm 5 → 1.
3. Repair từ raw snapshot → quality/freshness trở lại PASS/FRESH → cả bốn metrics trở về đúng baseline với delta 0.0000.

Kết luận được giới hạn theo evidence: không phải mọi corruption đều chứng minh được tác động riêng trên locked test set, và `retrieval_hit_rate` không giảm. Do đó cần dùng đồng thời retrieval, answer, quality và freshness metrics.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Sau khi merge/pull, embedding manifests chứa path tuyệt đối từ máy thành viên khác và CP6 release hash của baseline manifest không khớp file hiện tại; một số generated JSON từng có merge marker.
- **Nguyên nhân:** Chroma persist path được ghi theo absolute path phụ thuộc máy; generated artifacts bị nhiều branch cùng sửa; release hashes được refresh không đồng bộ.
- **Cách xử lý:** Manifest chuyển sang path portable `data/chroma`; loader chỉ chấp nhận path trong project và fallback về configured Chroma path; conflict markers được loại bỏ; Chroma SQLite generated được đưa vào `.gitignore` và bỏ khỏi Git index; CP6 release check regenerate reports và artifact hashes.
- **Cách xác minh:** JSON validation 24/24 PASS, conflict marker 0, ba collections mỗi collection 24 documents, compile PASS, `git diff --check` PASS và `checkpoint6_release_check.json` báo `ready_for_release` với 22/22 checks.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Corpus chỉ có 24 paper và 24 câu hỏi | Metrics chưa đại diện cho nhiều domain/query distribution | Mở rộng corpus và held-out test set; báo confidence interval theo nhiều lần chạy |
| Test set được sinh từ chính cleaned corpus | Có nguy cơ evaluation dễ và chưa đo generalization | Tạo test set độc lập, có human review và câu hỏi khó/không trả lời được |
| Ragas chưa bật | Chưa có Ragas faithfulness/context metrics | Chạy `RUN_RAGAS=1`, lưu riêng kết quả và không thay đổi evaluation contract |
| LLM judge có thể biến thiên | Judge metrics có thể thay đổi giữa các lần API call | Pin model/prompt, chạy lặp và báo mean/std; thêm human spot-check |
| Một số corruption không nằm trong locked test cases | Chưa đo được impact riêng của mọi corruption | Thêm targeted questions cho từng affected record trước khi khóa test set mới |
| Retrieval chỉ dùng dense MiniLM | Có thể bỏ lỡ exact keyword hoặc DOI cases | So sánh hybrid retrieval/reranking trên cùng corpus và test set |
| UI OpenAI Agent cần internet/API key | Demo provider-dependent có thể thất bại do network | Giữ Local QA fallback, chạy smoke trước demo và không coi provider failure là pipeline failure |

## 13. Checklist trước khi nộp

- [ ] Nhóm bổ sung họ tên/MSSV của Role 1, Role 4 và Role 5 ở Mục 1.
- [x] Repository, tên nhóm và khóa học đã được ghi.
- [x] Phân công khớp với module, artifact và vai trò trong HTML.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set đã khóa hash.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Raw, clean, embedding, evaluation, results, quality và reports artifacts đều tồn tại.
- [x] Corruption log truy vết được type, parameters và affected record IDs.
- [x] CP6 release check đạt 22/22 PASS.
- [ ] Mỗi thành viên hoàn thành và xác nhận individual report riêng.
- [x] `.env` và API key không được Git track hoặc ghi vào report.
