# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                |
| --------------- | ----------------------------------------------------------------------- |
| Họ và tên       | Nguyễn Quang Minh                                                       |
| MSSV            | 2A202601955                                                             |
| Khóa/Lớp        | K3                                                                      |
| Tên nhóm        | No Name                                                                 |
| Vai trò chính   | Role 2 — Ingestion owner (Crossref + raw lineage)                       |
| Repository      | https://github.com/BLonggg608/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                                                              |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable                         | File/hàm phụ trách                                                       | Input nhận vào                          | Output bàn giao                                                                                           | Trạng thái |
| ------------------------------------------ | ------------------------------------------------------------------------ | --------------------------------------- | --------------------------------------------------------------------------------------------------------- | ---------- |
| Parse Crossref payload thành `PaperRecord` | `src/ingestion/crossref.py::parse_crossref_payload`                      | Raw JSON payload từ Crossref REST API   | `list[PaperRecord]` (paper_id = DOI lowercase, title, summary, authors, dates, URLs)                      | Hoàn thành |
| Fetch nguồn + lưu raw snapshot             | `src/ingestion/crossref.py::fetch_source_records`, `_request_with_retry` | `Settings` (query, filter, max_results) | `data/raw/crossref_response.json` (raw response gốc), `data/raw/crossref_records.json` (records đã parse) | Hoàn thành |
| Load lại raw snapshot không cần gọi API    | `src/ingestion/crossref.py::load_raw_records`                            | Đường dẫn JSON snapshot                 | `list[PaperRecord]`                                                                                       | Hoàn thành |

Chỉ nhận ownership cho phần bạn trực tiếp thực hiện. Liên hệ rõ phần việc của bạn với đầu vào, đầu ra và các thành viên phụ thuộc vào phần đó.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                                                                           | Thành viên/module được hỗ trợ                                                    | Kết quả                                                                                                                       |
| --------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| Sửa lỗi `UnicodeEncodeError` khi log tiếng Việt bằng `print()` trên console Windows (cp1252)        | `src/ingestion/cleaning.py` (Role 3 — Clean & corruption owner)                  | Đổi `print()` sang `logger.info()`; xác nhận chạy lại không crash, vẫn ghi đủ log cleaning                                    |
| Implement report so sánh corruption còn thiếu, đang chặn `run_corruption_flow.py`                   | `src/observability/reporting.py::generate_corruption_report` (Role Eval/Observe) | Sinh `data/reports/corruption_report.md` so sánh baseline/corrupted/repaired kèm delta, giúp pipeline CP5 chạy hết end-to-end |
| Chạy thử `build_clean_dataframe` end-to-end bằng raw records của mình để xác nhận CP1 pass criteria | `src/ingestion/cleaning.py`                                                      | Sinh `data/clean/papers_clean.csv` / `.json`, xác nhận `paper_id` unique và `text_for_embedding`/`age_days` có mặt            |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                             | File/hàm/artifact liên quan                                    | Kết quả bàn giao                                                                                                             | Cách xác minh                                                                          |
| ----------------------------------------------------------------- | -------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Gọi Crossref API thật, lấy 24 paper liên quan RAG/LLM             | `fetch_source_records`                                         | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`                                                          | Chạy `fetch_source_records(load_settings())`, kiểm tra 2 file JSON tồn tại và đọc được |
| Đảm bảo `paper_id` (DOI) ổn định, không trùng                     | `parse_crossref_payload`                                       | 24/24 `paper_id` unique                                                                                                      | Script kiểm tra `Counter(paper_id)` không có DOI trùng                                 |
| Retry/backoff khi Crossref trả 429/503                            | `_request_with_retry`                                          | Không crash khi API tạm thời lỗi                                                                                             | Đọc code: exponential backoff 1.5s × 2^n, tối đa 5 lần thử                             |
| Đối chiếu raw → clean, đảm bảo Clean owner không phải đoán field  | `data/raw/crossref_records.json` → `data/clean/papers_clean.*` | Xác nhận `title`, `summary`, `authors`, `published` đầy đủ; `categories` trống ở toàn bộ 24 record (ghi chú cho Clean owner) | So sánh field trống trước/sau khi bàn giao                                             |
| Giữ raw source nguyên vẹn làm điểm phục hồi cho corruption/repair | `data/raw/crossref_records.json`                               | Repaired dataset ở CP5 dùng lại đúng raw này, không refetch API                                                              | `corruption_report.md`: repaired PASS 8/8 quality checks, freshness FRESH              |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/raw/crossref_records.json` — 24 `PaperRecord` lấy trực tiếp từ Crossref REST API, là nguồn duy nhất mà toàn bộ pipeline (clean → index → test set → evaluate → corrupt → repair) dựa vào. Ở CP5, khi record `10.2118/234689-pa` bị corruption drop khỏi dataset, chính raw snapshot này được dùng để build lại `papers_clean_repaired.*` và khôi phục đủ 24/24 record — quality check "Row count" và "paper_id duy nhất" chuyển từ FAIL (ở bản corrupted) sang PASS (ở bản repaired).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref REST API trả về JSON lồng nhau, không đồng nhất (field có thể thiếu, ngày tháng ở dạng `date-parts`, abstract lẫn thẻ XML/JATS, có thể trả lỗi tạm thời 429/503). Việc của Role 2 là biến payload thô đó thành `PaperRecord` — cấu trúc dữ liệu ổn định, sạch, có ID duy nhất — để các phần sau (cleaning, indexing, evaluation) không phải tự đoán format nguồn.

### Cách triển khai

- Dùng **DOI** (viết thường) làm `paper_id` vì DOI là định danh toàn cầu, không đổi theo thời gian — khác với title (có thể trùng/đổi) hoặc index thứ tự (không ổn định giữa các lần fetch).
- Bỏ qua (skip) record không có DOI, không có title, hoặc không parse được ngày `published` — tránh đưa dữ liệu rác vào pipeline thay vì cố "vá" bằng giá trị bịa.
- Tách abstract khỏi thẻ XML bằng regex `<[^>]+>` rồi gộp khoảng trắng thừa.
- Ngày tháng Crossref ở dạng `{"date-parts": [[Y, M, D]]}` — tự điền `month=1, day=1` nếu thiếu để luôn có ISO date hợp lệ.
- Gọi API qua `_request_with_retry`: exponential backoff (1.5s, 3s, 6s, 12s, 24s) chỉ cho status `429`/`503`; lỗi khác raise ngay vì retry không giúp ích.
- Luôn ghi **raw response gốc** ra đĩa (`raw_api_response`) trước khi parse — nếu logic parse sau này sai, vẫn còn bằng chứng gốc để sửa lại mà không cần fetch lại (tránh dữ liệu đổi giữa hai lần fetch làm baseline không tái lập được).

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input                   | `Settings.source_query`, `Settings.source_filter`, `Settings.max_results` (từ `core/config.py`); JSON payload Crossref `{"message": {"items": [...]}}`   |
| Output                  | `list[PaperRecord]` (dataclass frozen) + 2 file JSON: `crossref_response.json` (raw), `crossref_records.json` (đã parse)                                 |
| Module phụ thuộc        | `core.config.Settings`, thư viện `requests`                                                                                                              |
| Module sử dụng output   | `ingestion.cleaning.build_clean_dataframe` (Role 3), `pipelines.phase1.run_phase1`, `pipelines.corruption_flow.run_corruption_flow` (dùng raw để repair) |
| Điều kiện lỗi cần xử lý | Crossref trả 429/503 tạm thời; record thiếu DOI/title/ngày; JSON snapshot không tồn tại khi gọi `load_raw_records`                                       |

### Cách xác minh

```bash
.venv/Scripts/python.exe -c "
from core.config import load_settings
from ingestion.crossref import fetch_source_records
records = fetch_source_records(load_settings())
print(len(records), records[0])
"
```

- **Kết quả mong đợi:** Nhận được danh sách `PaperRecord`, hai file JSON được ghi ra `data/raw/`.
- **Kết quả thực tế:** Fetch thành công 24 record thật từ Crossref; `data/raw/crossref_response.json` (238KB) và `crossref_records.json` (56KB) được tạo; `paper_id` unique 24/24; không có duplicate.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn field nào của Crossref làm `paper_id` ổn định để toàn bộ pipeline (clean/index/eval/corrupt/repair) dùng chung một khóa duy nhất.
- **Các phương án đã cân nhắc:** (1) Dùng `title` chuẩn hoá làm ID; (2) Dùng thứ tự record trong response (index) làm ID; (3) Dùng `DOI` làm ID.
- **Phương án đã chọn:** DOI (lowercase).
- **Lý do:** Title có thể trùng giữa các paper khác nhau hoặc thay đổi cách viết hoa/khoảng trắng giữa các lần fetch; index theo thứ tự response không ổn định vì Crossref có thể trả về thứ tự khác nhau giữa các lần gọi cùng query. DOI là định danh học thuật toàn cầu, cố định vĩnh viễn cho một paper — đảm bảo `paper_id` nhất quán giữa raw → clean → baseline → corrupted → repaired.
- **Bằng chứng quyết định phù hợp:** Kiểm tra `Counter(paper_id)` trên 24 record: không có DOI trùng lặp; ở CP5, sau khi corruption drop 1 record theo `paper_id`, repair từ raw khôi phục đúng record đó bằng chính DOI đó — chứng minh ID đủ ổn định để trace xuyên suốt pipeline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```
  UnicodeEncodeError: 'charmap' codec can't encode character 'Ế' in position 15: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `build_clean_dataframe(records, run_date)` trên Windows console mặc định (không set `PYTHONIOENCODING`).
- **Nguyên nhân gốc:** `src/ingestion/cleaning.py` dùng `print()` để in log tiếng Việt có dấu; Windows console mặc định dùng encoding `cp1252`, không encode được các ký tự Unicode ngoài bảng đó (ví dụ `Ế`, `ộ`) → chương trình crash giữa chừng khi đang cleaning.
- **Cách xử lý:** Đổi toàn bộ `print(...)` trong `build_clean_dataframe` sang `logger.info(...)` (module `logging` đã sẵn `logger` nhưng chưa được dùng) — logging tự xử lý lỗi encode nội bộ (`handleError`) thay vì để exception văng ra làm chết chương trình.
- **Cách xác minh sau khi sửa:** Chạy lại `build_clean_dataframe` không set `PYTHONIOENCODING` — chương trình chạy hết, trả về DataFrame 24 dòng, không còn traceback.
- **Điều học được:** Không nên dùng `print()` cho log có ký tự Unicode trong pipeline chạy trên nhiều môi trường (Windows/Linux/CI) — `logging` an toàn hơn vì không làm crash toàn bộ pipeline chỉ vì một dòng log không encode được.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref → vector index:** `fetch_source_records` gọi Crossref REST API → lưu raw response + parse thành `PaperRecord` → `build_clean_dataframe` (Role 3) chuẩn hoá thành DataFrame có `text_for_embedding` → `LocalEmbeddingIndex.build` (Role RAG) dùng MiniLM encode `text_for_embedding` thành vector, lưu vào Chroma collection (`papers-baseline`/`papers-corrupted`/`papers-repaired` tuỳ trạng thái).
2. **Test set và ground-truth doc IDs:** `build_test_set` (Role Eval) sinh câu hỏi (summary/authors/date/categories) từ chính clean dataframe, với `ground_truth_doc_ids` lấy trực tiếp từ `paper_id` đã có trong clean data — không tự bịa ID, để khi evaluate, retrieval_hit_rate có thể so khớp chính xác document nào được trả về so với document đúng.
3. **Quality checks vs freshness monitoring:** Quality checks (`run_data_quality_checks`) đo tính đúng đắn cấu trúc dữ liệu tại một thời điểm — completeness (không rỗng), uniqueness (`paper_id` không trùng), validity (`age_days` hợp lệ). Freshness monitoring đo tính "mới" theo thời gian — so `published` với ngưỡng `freshness_threshold_days` (180 ngày) để phát hiện dữ liệu cũ, không liên quan gì đến việc dữ liệu có đúng schema hay không.
4. **Vì sao dùng chung test set cho ba trạng thái:** Để so sánh công bằng — nếu mỗi trạng thái dùng test set khác nhau, sự thay đổi metric có thể do câu hỏi khác nhau chứ không phải do chất lượng dữ liệu thay đổi. Giữ nguyên test set/ground truth là điều kiện tiên quyết để mọi delta (baseline vs corrupted vs repaired) phản ánh đúng tác động của corruption/repair.
5. **Repair thành công dựa trên gì:** Repaired dataset được build lại từ raw snapshot gốc (không sửa tay), sau đó re-evaluate bằng đúng test set cũ. Trong `corruption_report.md`: repaired đạt PASS 8/8 quality checks (so với corrupted chỉ 5/8), freshness FRESH (so với STALE ở corrupted), và các metric (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) quay về đúng bằng giá trị baseline (delta = 0.0000) — đây là bằng chứng repair thành công, không chỉ dựa vào "script chạy không lỗi".

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline |                                                    Corrupted | Repaired | Nhận xét của cá nhân                                                                                                      |
| -------------------- | -------: | -----------------------------------------------------------: | -------: | ------------------------------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 |                                                       1.0000 |   1.0000 | Không đổi — retrieval vẫn tìm đúng doc dù dữ liệu bị corrupt nhẹ (24 record, chỉ 1 record/loại lỗi mỗi lần)               |
| `mean_token_f1`      |   1.0000 |                                                       0.8414 |   1.0000 | Giảm rõ ở corrupted (do `truncate_title` và `blank_summary` làm answer text mất thông tin), phục hồi hoàn toàn sau repair |
| `judge_accuracy`     |   0.9583 |                                                       0.7917 |   0.9583 | Giảm mạnh nhất trong các metric — LLM judge nhạy với nội dung bị hỏng (noise/blank) hơn retrieval                         |
| `mean_judge_score`   |   4.8333 |                                                       4.2500 |   4.8333 | Cùng xu hướng với judge_accuracy                                                                                          |
| Quality checks       | 8/8 PASS | 5/8 PASS (FAIL: uniqueness, summary completeness, freshness) | 8/8 PASS | Corruption gây FAIL đúng 3 dimension bị tác động trực tiếp (duplicate row, blank summary, stale date)                     |
| Freshness status     |    FRESH |                                  STALE/INVALID (1 stale row) |    FRESH | `stale_publication_date` (+730 ngày) đẩy 1 record vượt ngưỡng 180 ngày                                                    |

### Kết luận từ số liệu

1. **[Blank summary + inject noise vào summary]** → **[quality check "summary không rỗng" FAIL, `text_for_embedding` chứa nội dung rác]** → **[`mean_token_f1` giảm từ 1.0 xuống 0.8414 vì answer text mất nội dung/nhiễu]**.
2. **[Repair: reload từ raw snapshot, build lại clean dataframe]** → **[toàn bộ 8/8 quality checks PASS trở lại, freshness FRESH]** → **[toàn bộ 4 metric phục hồi về đúng giá trị baseline (delta = 0.0000)]**.

Corruption nào ảnh hưởng rõ nhất và vì sao?

`blank_summary` và `inject_summary_noise` ảnh hưởng rõ nhất đến `mean_token_f1` và `judge_accuracy` — vì `text_for_embedding` và answer generation phụ thuộc trực tiếp vào nội dung `summary`; xoá hoặc làm nhiễu summary trực tiếp làm giảm chất lượng câu trả lời của agent, trong khi `drop_latest_records` hay `truncate_title` chỉ ảnh hưởng gián tiếp (retrieval vẫn tìm đúng các doc còn lại nhờ chỉ 1/24 record bị tác động mỗi loại).

Kết quả nào khác với kỳ vọng ban đầu?

Ban đầu dự đoán `retrieval_hit_rate` cũng sẽ giảm ở bản corrupted vì có record bị drop, nhưng thực tế giữ nguyên 1.0000 — đã kiểm tra lại: do tỷ lệ corruption thấp (5%/loại trên 24 record, mỗi loại chỉ ảnh hưởng 1 record) và top-k=4 đủ rộng nên câu hỏi trong test set vẫn tìm được đúng document liên quan trong số các record còn lại, dù dataset có bị corrupt.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Chọn ID ổn định (DOI thay vì title/index) ngay từ bước ingestion là quyết định ảnh hưởng đến toàn bộ khả năng trace lineage của pipeline — sai ở bước đầu sẽ lan ra mọi bước sau.
2. Giữ raw response gốc (chưa parse) là "bảo hiểm" quan trọng: khi corruption làm hỏng clean data, có raw snapshot nghĩa là luôn repair được về đúng trạng thái ban đầu mà không cần gọi lại API (tránh dữ liệu đổi giữa các lần fetch).
3. Corruption ảnh hưởng đến các metric agent (`judge_accuracy`, `mean_token_f1`) rõ hơn nhiều so với `retrieval_hit_rate` — dữ liệu "tìm được" không có nghĩa là dữ liệu "dùng được"; cần nhìn nhiều loại metric cùng lúc mới thấy hết tác động của data quality kém.

### Nếu có thêm thời gian

Sẽ tăng tỷ lệ corruption (ví dụ 20-30% thay vì 5%) và test với nhiều query hơn để đo rõ hơn ngưỡng mà `retrieval_hit_rate` bắt đầu giảm — hiện tại 5%/24 record là quá nhỏ để thấy tác động lên retrieval, cần benchmark ở mức corruption cao hơn để biết pipeline chịu được đến đâu trước khi retrieval thực sự sai.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Quang Minh
**Ngày xác nhận:** 2029-08-06
