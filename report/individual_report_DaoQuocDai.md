# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đào Quốc Đại |
| MSSV | 2A202601285 |
| Khóa/Lớp | K3 |
| Tên nhóm | No Name |
| Vai trò chính | Role 1 — Điều phối pipeline (cấu hình, orchestration, release) |
| Repository | https://github.com/BLonggg608/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình dùng chung | `src/core/config.py` | Biến môi trường và `.env` cục bộ | Đối tượng `Settings`, đường dẫn và tham số dùng chung | Hoàn thành |
| Hợp đồng orchestration | `src/core/orchestration.py` | Settings, tên trạng thái và artifact path | Quy ước baseline/corrupted/repaired nhất quán | Hoàn thành |
| Điều phối baseline | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw/clean data, test set, provider config | Clean data, index, answers, metrics, quality/freshness report | Hoàn thành |
| Điều phối corruption và repair | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Raw snapshot, baseline clean và test set đã khóa | Corrupted/repaired artifacts và báo cáo so sánh | Hoàn thành |
| Release gate | `script/run_release_check.py` | Toàn bộ artifact của ba trạng thái | JSON kiểm tra máy đọc được và release review Markdown | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp đầu ra của 4 role còn lại vào một luồng chạy | Ingestion, cleaning/corruption, RAG/agent, evaluation/observability | Pipeline chạy theo đúng handoff raw → clean → index → evaluate → report |
| Đồng bộ artifact sau khi merge | Các role tạo JSON và Chroma artifacts | Loại merge marker khỏi artifact, giữ dữ liệu thật từ lần chạy hợp lệ và xác nhận JSON đọc được |
| Chuẩn hóa đường dẫn artifact | Retrieval và reporting | Manifest/report dùng đường dẫn tương đối, chạy được khi repository nằm ở máy khác |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chốt cấu hình và đường dẫn dùng chung | `src/core/config.py`, `src/core/orchestration.py` | Ba trạng thái có path và collection riêng, tránh ghi đè lẫn nhau | Kiểm tra release checks `baseline_collection`, `corrupted_collection`, `repaired_collection` |
| Ghép pipeline baseline end-to-end | `src/pipelines/phase1.py` | 24 samples, quality 8/8 PASS, freshness FRESH | `uv run python script\run_phase1.py` |
| Ghép luồng corrupt → repair → compare | `src/pipelines/corruption_flow.py` | Corrupted giảm metric; repaired trở về baseline | `uv run python script\run_corruption_flow.py` |
| Khóa điều kiện so sánh công bằng | `data/eval/test_set.json` | Cả ba trạng thái dùng cùng 24 câu hỏi; SHA-256 được kiểm tra | `certutil -hashfile data\eval\test_set.json SHA256` |
| Xây release gate | `script/run_release_check.py` | 22/22 checks PASS, trạng thái READY FOR RELEASE | `uv run python script\run_release_check.py` |

Artifact tổng hợp quan trọng nhất của vai trò là `data/results/checkpoint6_release_check.json`. File này lưu từng điều kiện release và bằng chứng tương ứng; bản đọc cho con người nằm tại `data/reports/checkpoint6_release_review.md`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các module do nhiều thành viên phát triển phải ghép thành một pipeline có thứ tự rõ ràng, dùng chung data contract và không ghi đè artifact. Ngoài việc chạy được, bản release phải chứng minh rằng baseline, corrupted và repaired được đánh giá trên cùng điều kiện; repair phải dựng lại từ raw snapshot thay vì sửa tay hoặc fetch dữ liệu mới.

### Cách triển khai

Pipeline baseline điều phối ingestion → cleaning → test set/index → agent evaluation → quality/freshness/report. Luồng corruption giữ nguyên test set, tạo dataset và collection riêng, đánh giá lại rồi repair bằng cách chạy cleaning từ raw snapshot đã lưu. Release checker đọc artifact độc lập để kiểm tra số record, ID câu hỏi, hash test set, metrics, quality/freshness, Chroma collections, corruption lineage, secret, TODO và merge marker. Một check thất bại thì không được kết luận READY FOR RELEASE.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `.env` cục bộ; raw Crossref snapshot; clean schema; evaluation set gồm `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| Output | Artifact tách riêng theo `baseline`, `corrupted`, `repaired`; metrics JSON; quality/freshness JSON; comparison và release report |
| Module phụ thuộc | `ingestion`, `retrieval`, `agent`, `evaluation`, `observability` |
| Module sử dụng output | Script demo, báo cáo nhóm và release checker |
| Điều kiện lỗi cần xử lý | Thiếu artifact, sai số record/ID, đổi test set, dùng evaluator fallback, collection sai, repair lệch baseline, lộ secret, merge marker hoặc path tuyệt đối |

### Cách xác minh trên Windows CMD

```bat
set PYTHONUTF8=1
uv run python script\run_phase1.py
uv run python script\run_corruption_flow.py
uv run python script\run_release_check.py
type data\reports\checkpoint6_release_review.md
```

- **Kết quả mong đợi:** Pipeline tạo đủ ba trạng thái và release gate PASS.
- **Kết quả thực tế:** 22/22 release checks PASS; 24 raw records, 24 test questions, 24 answers cho mỗi trạng thái; ba Chroma collections đều có 24 documents.
- **Artifact/log:** `data/results/checkpoint6_release_check.json`, `data/reports/checkpoint6_release_review.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần bảo đảm delta metric đến từ thay đổi dữ liệu, không phải do câu hỏi, ground truth, collection hoặc dữ liệu nguồn thay đổi.
- **Các phương án đã cân nhắc:** (1) Mỗi trạng thái tự sinh lại test set và dùng chung collection; (2) khóa một test set, tách collection/artifact theo trạng thái và repair từ raw snapshot.
- **Phương án đã chọn:** Khóa cùng một evaluation set bằng SHA-256, tách `papers-baseline`, `papers-corrupted`, `papers-repaired`, và rebuild repaired data từ raw snapshot.
- **Lý do:** Phương án này cô lập biến dữ liệu, giữ khả năng tái lập và tránh việc một lần fetch Crossref mới làm thay đổi mẫu so sánh.
- **Bằng chứng:** Test-set hash là `90D8ED972B2DBBB84C35E22FB8E0DFE9B775839433A05065B2242C7836083139`; release checks xác nhận cả ba evaluation contract có 24 samples và repaired metrics có delta bằng 0 so với baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Sau khi đồng bộ code nhóm, một số JSON artifact chứa Git conflict marker; đồng thời thay đổi từ remote có thể xóa `data/chroma/chroma.sqlite3`.
- **Bước tái hiện:** Chạy tìm `<<<<<<<`, `=======`, `>>>>>>>` trong các file được track và kiểm tra `git status` sau merge.
- **Nguyên nhân gốc:** Artifact sinh tự động được nhiều nhánh commit cùng lúc nên Git không thể merge theo ngữ nghĩa JSON/SQLite.
- **Cách xử lý:** Đối chiếu parent hợp lệ, giữ artifact thật từ lần chạy đã xác minh, không tự sửa metric; giữ Chroma database cần cho demo, sau đó kiểm tra lại toàn bộ JSON và chạy release checker.
- **Cách xác minh sau khi sửa:** Release check `no_student_todo_or_merge_marker` PASS, ba collection đều đọc được 24 documents, tổng cộng 22/22 checks PASS.
- **Điều học được:** Generated artifact vẫn cần ownership rõ ràng; với file nhị phân/JSON kết quả, nên tái tạo có kiểm soát hoặc chọn nguồn đã xác minh thay vì merge thủ công từng đoạn.

## 7. Hiểu biết về luồng end-to-end

1. Crossref được gọi với retry/backoff, raw response và parsed records được lưu trước. Cleaning chuẩn hóa thành clean schema và tạo `text_for_embedding`; module index mã hóa trường này rồi ghi document vào Chroma.
2. Evaluation set giữ question, ground truth và `ground_truth_doc_ids`. Evaluator so ID truy xuất với doc ID đúng để tính hit rate, đồng thời so nội dung câu trả lời để tính token F1 và dùng LLM judge cho accuracy/score.
3. Quality checks đo completeness, uniqueness và validity của dataset. Freshness đo độ mới theo ngày xuất bản và ngưỡng thời gian; dữ liệu có thể đúng schema nhưng vẫn stale.
4. Ba trạng thái bắt buộc dùng cùng test set để delta phản ánh corruption/repair, không phản ánh độ khó khác nhau của câu hỏi.
5. Repair thành công khi clean repaired khớp baseline, quality/freshness phục hồi và agent metrics quay lại baseline. Việc script không báo lỗi là chưa đủ bằng chứng.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | Top-k vẫn tìm thấy đúng tài liệu; riêng metric này không phát hiện hết lỗi nội dung |
| `mean_token_f1` | 1.0000 | 0.8414 | 1.0000 | Nội dung bị xóa/nhiễu làm chất lượng câu trả lời giảm rõ rệt |
| `judge_accuracy` | 0.9583 | 0.7917 | 0.9583 | LLM judge nhận ra suy giảm chất lượng dù hit rate không đổi |
| `mean_judge_score` | 4.8333 | 4.2500 | 4.8333 | Phục hồi hoàn toàn sau repair |
| Quality checks | 8/8 PASS | 5/8 PASS | 8/8 PASS | Phát hiện duplicate, summary rỗng và freshness lỗi |
| Freshness status | FRESH | STALE (1 row) | FRESH | Theo dõi được lỗi thời gian độc lập với answer metrics |

Chuỗi nguyên nhân–bằng chứng:

1. Corruption tạo duplicate, summary rỗng/nhiễu và record stale → quality giảm 8/8 xuống 5/8, freshness chuyển FRESH → STALE → token F1 giảm 0.1586, judge accuracy giảm 0.1667 và mean judge score giảm 0.5833.
2. Repair chạy lại từ raw snapshot → clean data khớp baseline, quality trở lại 8/8 và freshness FRESH → toàn bộ metric repaired trở về baseline.

Corruption nội dung summary ảnh hưởng rõ nhất đến answer quality vì summary tham gia trực tiếp vào embedding và câu trả lời. Kết quả khác kỳ vọng là `retrieval_hit_rate` vẫn 1.0; điều này cho thấy retrieval hit không đủ để kết luận hệ thống khỏe, cần đọc cùng token F1, LLM judge và data-quality signals. Cả ba lượt đều có `judge_mode = llm`, `fallback_judge_samples = 0`; Ragas chưa bật nên báo cáo không đưa kết luận dựa trên Ragas.

## 9. Điều học được và hướng cải thiện

1. Orchestration không chỉ là gọi hàm theo thứ tự; nó phải khóa contract, lineage và namespace artifact để kết quả có thể so sánh.
2. Release gate cần kiểm tra bằng chứng máy đọc được, không chỉ dựa vào log “chạy thành công”.
3. Một RAG system có thể retrieval đúng nhưng answer vẫn kém khi nội dung nguồn hỏng; observability phải theo dõi cả dữ liệu và downstream metrics.

Nếu có thêm thời gian, tôi sẽ đưa release checker vào CI và quy định generated artifact nào được commit. Cải thiện được đo bằng việc mỗi pull request tự động chạy các check không cần API, còn bộ đánh giá LLM được chạy ở release job có secret quản lý riêng.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đào Quốc Đại  
**Ngày xác nhận:** 2026-08-06
