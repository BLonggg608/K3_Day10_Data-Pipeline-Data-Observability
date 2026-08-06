# Member Role Report — Day 10: Data Pipeline & Data Observability

> Báo cáo dành riêng cho **Role 3: Clean Schema, Corruption, Repair**. Phần thông tin cá nhân và điểm số Metrics được để trống `[ ]` để bạn tự điền.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Đặng Trần Trung Dũng     |
| MSSV               | 2A202601785                    |
| Khóa/Lớp         | K3              |
| Tên nhóm         | No Name    |
| Vai trò chính    | Role 3 - Clean schema, corruption, repair |
| Repository         | https://github.com/BLonggg608/K3_Day10_Data-Pipeline-Data-Observability.git |
| Ngày hoàn thành | 2026-08-07               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------------- |
| Xây dựng schema làm sạch dữ liệu (Cleaning) | `src/ingestion/cleaning.py` (`build_clean_dataframe`) | Dữ liệu thô (List[PaperRecord]) từ bước ingestion | `clean.csv`, `clean.json` (DataFrame đã lọc rác, dedupe) | Hoàn thành |
| Mô phỏng lỗi dữ liệu có chủ đích (Corruption) | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | Dữ liệu sạch (Clean DataFrame) | `corrupted_clean.csv`, `corruption_log.json` | Hoàn thành |
| Tái tạo dữ liệu từ snapshot (Repair) | `src/pipelines/corruption_flow.py` (cùng các bạn ghép nối pipeline) | `raw_records.json` (Snapshot dữ liệu thô) | `repaired_clean.csv` (Đã được làm sạch lại 100%) | Hoàn thành |


### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Lọc bản ghi lỗi và format text cho embedding | `cleaning.py` | Tạo ra cột `text_for_embedding` chứa chuỗi văn bản sạch để LLM đọc. | Chạy `python script/test_cleaning.py` và kiểm tra DataFrame in ra terminal. |
| Tiêm lỗi (noise, stale, missing, duplicate) vào dữ liệu | `corruption.py` | Artifact: `data/reports/corruption_log.json` | Chạy `python script/run_corruption_flow.py` và kiểm tra log JSON xem ID có đúng bị tác động không. |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
**Output:** File `corruption_log.json` lưu lại cực kỳ chi tiết lịch sử "phá hoại" dữ liệu (bao gồm tên loại lỗi, tham số, số lượng bị ảnh hưởng và danh sách chính xác các `paper_id` bị tác động) giúp quá trình debug và so sánh trước-sau dễ dàng hơn.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Dữ liệu thô (raw data) kéo từ API bên ngoài (Crossref) luôn chứa nhiều rác: bài báo thiếu nội dung, trùng lặp ID, hoặc có ngày xuất bản quá cũ. Nếu đưa nguyên đống rác này vào Vector Database (ChromaDB), Agent LLM khi tìm kiếm (Retrieval) sẽ lấy ra ngữ cảnh sai, từ đó trả lời (Answer) sai hoặc Halucinate (ảo giác). Nhiệm vụ của Role 3 là phải xây dựng chốt chặn lọc rác này, đồng thời tạo ra một phiên bản "bị hỏng" có chủ ý để chứng minh tầm quan trọng của việc làm sạch bằng các bài test đánh giá.

### Cách triển khai
- **Cleaning:** Sử dụng pandas để thao tác trên DataFrame: `dropna` với các cột cốt lõi (title, summary), `drop_duplicates(subset=['paper_id'], keep='first')` sau khi sort `updated_dt` giảm dần để giữ bản ghi mới nhất. Chuỗi hóa list authors/categories, tính toán độ cũ/mới `age_days`.
- **Corruption:** Dùng cơ chế deterministic/index matching để lấy chính xác các dòng mục tiêu, sau đó thực hiện các nghiệp vụ: tiêm ký tự lạ `[NOISE]` vào cột text, ép `published_dt` lùi lại `pd.Timedelta(days=730)`, cắt gọt (truncate) text, copy và `pd.concat` bản ghi để tạo duplicated.
- **Repair:** Thay vì sửa tay từ bản corrupted, hệ thống tự động repair triệt để bằng cách load lại raw snapshot và cho chạy qua luồng `build_clean_dataframe` một lần nữa, đảm bảo tính Reproducibility (khả năng tái hiện độc lập).

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Danh sách các dataclass `PaperRecord` raw hoặc Clean DataFrame. |
| Output                         | `pd.DataFrame` được định dạng chuẩn, có cột `text_for_embedding` và `age_days`. |
| Module phụ thuộc             | `src/ingestion/crossref.py` (cung cấp schema gốc). |
| Module sử dụng output        | `src/retrieval/index.py` (cần output sạch để tạo Chunk, nhét vào DB). |
| Điều kiện lỗi cần xử lý | Xử lý TypeError khi trừ pd.Timedelta cho chuỗi string (do đọc từ file CSV). |

### Cách xác minh

```bash
python script/run_corruption_flow.py
```
- **Kết quả mong đợi:** Script chạy mượt mà từ đầu đến cuối, xuất ra các file CSV sạch, corrupted, repaired và báo cáo so sánh metrics.
- **Kết quả thực tế:** Chạy thành công. Báo cáo sinh ra thể hiện rõ Ragas metric bị giảm khi dùng bản corrupted.
- **Artifact/log:** `data/reports/corruption_report.md` và `data/reports/corruption_log.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Xử lý lỗi phép trừ ngày tháng `TypeError` ở file `corruption.py` khi chạy flow tổng.
- **Các phương án đã cân nhắc:** 
  1) Convert cột sang `datetime` ngay từ khi đọc CSV.
  2) Chủ động ép kiểu (`pd.to_datetime`) ngay trong hàm `corrupt_clean_dataframe` khi thao tác.
- **Phương án đã chọn:** Phương án 2 (Ép kiểu chủ động trong hàm corruption).
- **Lý do:** Giúp hàm độc lập và an toàn (robust), bất kể nó nhận vào một DataFrame được load từ bộ nhớ hay được load lên từ một file văn bản (CSV). Nó tự bảo vệ schema của nó mà không phụ thuộc vào script gọi nó.
- **Bằng chứng quyết định phù hợp:** Script `run_corruption_flow.py` trước đây bị crash, sau khi thêm xử lý ép kiểu đã vượt qua trót lọt không dính lỗi Type Mismatch.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: operation 'sub' not supported for dtype 'str' with object of type <class 'pandas.Timedelta'>`
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_corruption_flow.py`
- **Nguyên nhân gốc:** Dữ liệu sạch ban đầu được lưu ra ổ cứng dưới dạng CSV. Khi được load lên lại bằng pandas, cột ngày tháng `published_dt` bị nhận dạng là kiểu String thay vì datetime object. Dẫn đến việc không thể thực hiện phép toán lùi ngày (Timedelta).
- **Cách xử lý:** Bổ sung dòng code ép kiểu `corrupted_df['published_dt'] = pd.to_datetime(...)` ngay trước khi thực hiện phép trừ ngày ở phần *Stale publication date*.
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_corruption_flow.py` và thành công.
- **Điều học được:** Cần rất cẩn trọng với Data Type khi thực hiện I/O (Lưu - Đọc) từ file text (CSV/JSON), các Meta-type như datetime rất dễ bị mất định dạng.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** 
   Gọi API Crossref -> Lấy JSON thô (Ingestion) chuyển thành PaperRecord -> Đi qua `cleaning.py` lọc rác, tính age, nối text -> Chia nhỏ (chunking) -> Đưa vào Embedding Model -> Lưu vào ChromaDB (Index).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** 
   Evaluation set chứa các câu hỏi mẫu và câu trả lời kỳ vọng. Ground-truth document IDs so khớp với các ID mà ChromaDB lôi ra (Retrieval) để tính điểm Precision (lấy đúng/sai bao nhiêu). LLM-as-a-judge sẽ chấm xem câu trả lời được sinh ra có bám sát ground truth (Faithfulness/Relevancy) hay không.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** 
   Quality checks đo độ hoàn thiện (không có Null, duy nhất ID, đúng schema). Còn Freshness monitoring đo độ "tươi" của dữ liệu (bài báo xuất bản cách đây bao lâu, có quá cũ so với ngưỡng threshold hay không).
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** 
   Để đảm bảo tính công bằng (A/B Testing). Đề thi (test set) phải không đổi thì ta mới so sánh được ảnh hưởng duy nhất là do chất lượng của bộ Data (Corrupted kém hơn Repaired).
5. **Repair được xem là thành công dựa trên artifact và metric nào?** 
   Artifact `repaired_clean.csv` được sinh ra không còn rác, vượt qua được hàm `validate_clean_dataframe` và điểm Ragas metric của Repaired dataset phải khôi phục lại (tiệm cận hoặc bằng 100%) so với mức Baseline ban đầu.

## 8. Phân tích kết quả

*(Lưu ý: Bạn hãy tự điền điểm số thật từ báo cáo `corruption_report.md` sinh ra trên máy bạn vào bảng này nhé!)*

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |   1.0000 |    1.0000 |   1.0000 | Không thay đổi (Hit rate vẫn đạt 100% nhưng chất lượng nội dung retrieved có thể bị hỏng) |
| `mean_token_f1`      |   1.0000 |    0.8414 |   1.0000 | Giảm mạnh do rác/thiếu nội dung ở Corrupted, khôi phục 100% ở Repaired |
| `judge_accuracy`     |   0.9583 |    0.7917 |   0.9583 | LLM trả lời kém chính xác hơn ở bản Corrupted và khôi phục hoàn toàn khi Repair |
| `mean_judge_score`   |   4.8333 |    4.2500 |   4.8333 | Điểm đánh giá chất lượng câu trả lời giảm rõ rệt và khôi phục về mức cao ban đầu |
| Quality checks         |   8/8 PASS |   5 PASS/3 FAIL |   8/8 PASS | Báo lỗi trùng ID và thiếu summary ở bản Corrupted, vượt qua toàn bộ test khi Repair |
| Freshness status       |    FRESH |   STALE/INVALID |    FRESH | Phát hiện được bài báo cũ quá hạn (stale) ở bản Corrupted, khôi phục "tươi" hoàn toàn |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:
1. **Data corruption** → **Quality/freshness signal báo FAIL** → **Agent metric suy giảm nặng nề**.
2. **Repair action (Load từ Raw + Re-run Cleaning)** → **Quality/freshness signal phục hồi về PASS** → **Agent metric khôi phục lại ngang mức Baseline**.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Việc Blank summary (xóa nội dung) và tiêm rác (Noise) vào summary ảnh hưởng rõ nhất. Vì hệ thống RAG dùng nội dung này làm vector tìm kiếm. Mất nội dung => LLM không tìm thấy document liên quan (Retrieval rớt) => Trả lời ảo giác hoặc sai hoàn toàn (Answer Relevancy rớt).

**Kết quả nào khác với kỳ vọng ban đầu?**
*(Tự điền nếu có. Ví dụ: Cứ nghĩ làm lùi ngày (stale) sẽ kéo điểm xuống nhiều, nhưng LLM vẫn trả lời đúng nội dung nếu thông tin trong câu hỏi không gắn với mốc thời gian thực.)*

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Dữ liệu "Garbage In" sẽ dẫn tới "Garbage Out". Bất cứ Model xịn nào cũng không thể cứu được một bộ dữ liệu rác.
2. **Về data observability:** Việc tạo thêm lớp log (chi tiết số lượng dòng tác động, trước/sau) đóng vai trò cực kỳ quan trọng khi hệ thống có lỗi, giúp truy vết (Traceability) nhanh chóng thay vì mò mẫm.
3. **Về ảnh hưởng của data đến RAG agent:** Quá trình chuẩn bị Text (text_for_embedding) ảnh hưởng sống còn đến điểm số Retrieval của Agent.

### Nếu có thêm thời gian

Nếu có thêm thời gian, em sẽ bổ sung thêm các bộ test-case cho Cleaning, chạy giả lập với các bộ data cực đoan hơn (chứa script XSS, ký tự Emoji hỏng) để kiểm tra độ trâu bò (Robustness) của hàm `build_clean_dataframe`. Đồng thời viết Unit Test cho từng hành vi Corruption riêng lẻ.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Họ và tên của bạn]
**Ngày xác nhận:** [YYYY-MM-DD]
