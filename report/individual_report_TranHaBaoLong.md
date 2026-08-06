# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Trần Hà Bảo Long |
| MSSV | 2A202601189 |
| Khóa/Lớp | K3 |
| Tên nhóm | No Name |
| Vai trò chính | Role 4 — RAG & Agent Owner |
| Repository | https://github.com/BLonggg608/K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| MiniLM embedding và Chroma index | `src/retrieval/embeddings.py`, `src/retrieval/index.py` | Clean DataFrame có `paper_id`, `text_for_embedding` và metadata | Ba Chroma collections và ba embedding manifests | Hoàn thành |
| Semantic search và exact lookup | `LocalEmbeddingIndex.search`, `LocalEmbeddingIndex.lookup` | Query, `paper_id` hoặc exact title | Ranked `SearchResult` và document metadata | Hoàn thành |
| RAG agent có tools | `src/retrieval/agent.py` | Settings, index và factual question | Agent dùng `semantic_search_papers`/`lookup_paper` trước khi trả lời | Hoàn thành |
| Local factual QA dùng chung cho evaluation | `src/retrieval/qa.py` | Question, index và `top_k` | Answer, retrieved IDs, contexts và titles | Hoàn thành |
| Tách biệt ba trạng thái | `src/retrieval/index.py`, `data/embeddings/` | Baseline/corrupted/repaired clean artifacts | `papers-baseline`, `papers-corrupted`, `papers-repaired` | Hoàn thành |
| UI trình bày kết quả | `app.py` | Metrics, quality/freshness, corruption log và ba indexes | Streamlit dashboard gồm 4 tab, Local QA và OpenAI Agent mode | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra và sửa portability sau merge | Pipeline/release owner | Embedding manifest dùng `persist_path: data/chroma`, không còn absolute path theo máy thành viên |
| QA corrupted/repaired artifacts | Role 3 và Role 5 | Xác nhận ba manifests load được, mỗi collection có 24 documents, repaired metrics khớp baseline |
| Chuẩn hóa generated database trong Git | Toàn nhóm | `data/chroma/chroma.sqlite3` được ignore và bỏ khỏi Git index; chạy query không làm commit binary mới |
| Hỗ trợ report và demo | Role 5/nhóm | Report tiếng Việt, Streamlit dashboard thể hiện Baseline → Corrupted → Repaired bằng artifacts thật |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Build baseline index | `papers_embeddings.json`, `papers-baseline` | 24/24 clean documents được index | Load manifest và đếm Chroma collection |
| Build corrupted index riêng | `papers_embeddings_corrupted.json`, `papers-corrupted` | 24 documents, không ghi đè baseline | CP6 checks `baseline_collection` và `corrupted_collection` PASS |
| Build repaired index riêng | `papers_embeddings_repaired.json`, `papers-repaired` | 24 documents phục hồi từ raw-clean flow | CP6 check `repaired_collection` PASS |
| Chạy retrieval cùng evaluation contract | `baseline_answers.json`, `corrupted_answers.json`, `repaired_answers.json` | Mỗi trạng thái có 24 answers và retrieved IDs | CP6 evaluation contract checks PASS |
| Kiểm tra agent/tool contract | `build_agent`, `semantic_search_papers`, `lookup_paper` | Agent có hai tools và system prompt yêu cầu dùng tool cho factual question | Agent smoke test và source review |
| Xây UI so sánh | `app.py` | 4 tab: Tổng quan, Quality & Freshness, Corruption evidence, RAG Demo | Streamlit AppTest render 4 tab; Local QA query không có exception |

Output quan trọng nhất của vai trò là ba collection tách biệt `papers-baseline`, `papers-corrupted` và `papers-repaired`. Cả ba dùng cùng embedding model và retrieval contract, nhưng lấy dữ liệu từ ba artifacts khác nhau. Thiết kế này bảo vệ baseline khỏi bị mutate và cho phép so sánh công bằng ảnh hưởng của data corruption/repair lên retrieval và answer quality.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Clean data phải được chuyển thành vector index có thể tái lập, query được và truy vết về đúng `paper_id`. Khi corruption flow chạy, index corrupted không được ghi đè index baseline. Sau repair, hệ thống cần một index thứ ba để dùng cùng query/test set và chứng minh performance có phục hồi hay không. Agent cũng phải dùng corpus qua tools thay vì trả lời factual question chỉ bằng parametric knowledge của LLM.

### Cách triển khai

1. `LocalEmbeddingIndex._build_documents` chuyển mỗi row thành một document có `record_id`, `paper_id`, `title`, `content=text_for_embedding` và metadata gồm publication date, authors, categories, summary và URLs.
2. `MiniLMEmbeddings` dùng `sentence-transformers/all-MiniLM-L6-v2` để tạo vector. Chroma collection dùng cosine space; search score được quy đổi từ distance thành `max(0, 1 - distance)`.
3. Collection name được chọn theo embedding manifest path: baseline, corrupted hoặc repaired. Khi rebuild, chỉ collection tương ứng bị xóa/tạo lại, không mutate hai trạng thái còn lại.
4. Manifest lưu `persist_path` tương đối `data/chroma` để clone/pull trên máy khác vẫn load đúng database của project hiện tại.
5. `lookup` dùng hai map lowercase theo `paper_id` và exact title; `search` dùng query embedding và trả top-k ranked results.
6. Agent có hai LangChain tools: semantic search và exact lookup. System prompt yêu cầu gọi tool trước khi trả lời factual question và phải nói rõ khi corpus không hỗ trợ câu trả lời.
7. Streamlit UI đọc trực tiếp artifacts thật. Local QA chạy không cần API; OpenAI Agent mode dùng provider/model trong `.env`, hiển thị tool calls/results và cảnh báo nếu agent không gọi tool.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean DataFrame có `paper_id`, `title`, `published`, `authors_joined`, `categories_joined`, `summary`, `text_for_embedding`, `abs_url`, `pdf_url` |
| Embedding config | `sentence-transformers/all-MiniLM-L6-v2`, cosine space |
| Retrieval config | `top_k=4` mặc định; semantic search hoặc exact `paper_id`/title lookup |
| Output | Chroma collection, portable embedding manifest, `SearchResult`, answer và retrieved document IDs |
| Module phụ thuộc | `core.config.Settings`, `ingestion.cleaning`, ChromaDB, sentence-transformers, LangChain provider abstraction |
| Module sử dụng output | `evaluation.metrics`, `pipelines.phase1`, `pipelines.corruption_flow`, Streamlit `app.py` |
| Điều kiện lỗi | Thiếu manifest/collection; schema thiếu field; Chroma path từ checkout khác; embedding model chưa cache; provider hoặc API key chưa được cấu hình |

### Cách xác minh

```cmd
set PYTHONPATH=src
python script\run_phase1.py
python script\run_corruption_flow.py
python script\run_release_check.py
python -m streamlit run app.py
```

- **Kết quả mong đợi:** Ba manifests và ba collections tồn tại; mỗi collection có số documents khớp manifest; Local QA và exact lookup trả source IDs; CP6 release check PASS.
- **Kết quả thực tế:** `papers-baseline`, `papers-corrupted`, `papers-repaired` đều có 24 documents; CP6 đạt 22/22 PASS; Local QA trên UI chạy được cả ba trạng thái không có exception.
- **OpenAI UI:** Provider/model được nhận đúng là `openai`/`gpt-4o-mini`; UI dùng API key từ `.env`, chạy agent trên từng collection và hiển thị tool calls/tool results để nhóm kiểm tra grounding khi demo.
- **Artifact/log:** `data/embeddings/`, `data/results/*answers.json`, `data/results/checkpoint6_release_check.json`, `app.py`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần so sánh RAG giữa baseline, corrupted và repaired mà không làm mất baseline hoặc khiến kết quả phụ thuộc vào thứ tự chạy.
- **Các phương án đã cân nhắc:** (1) Dùng một Chroma collection rồi xóa/rebuild cho từng trạng thái; (2) dùng ba thư mục Chroma database riêng; (3) dùng một persist path và ba collection names riêng.
- **Phương án đã chọn:** Một persist path portable `data/chroma` với ba collection names: `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- **Lý do:** Một collection duy nhất dễ ghi đè baseline và làm demo không thể đối chiếu đồng thời. Ba database folders làm tăng generated files và khó quản lý Git. Ba collections trong cùng database giữ cấu hình nhất quán, query đồng thời được và vẫn tách biệt state.
- **Bằng chứng quyết định phù hợp:** CP6 xác nhận cả ba collections cùng tồn tại, mỗi collection 24 documents; baseline vẫn load/query được sau khi corrupted và repaired indexes được build. UI sử dụng ba collections trong cùng một lượt so sánh.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `LocalEmbeddingIndex.load()` không load đúng Chroma collection khi project được chạy ở một thư mục khác với nơi manifest được tạo. Trường `persist_path` trong embedding manifest trỏ tới absolute path của máy cũ, nên Chroma client có thể mở sai database hoặc báo không tìm thấy collection.
- **Bước tái hiện:** Build index tại một project path, sau đó copy/move project sang path khác và gọi `LocalEmbeddingIndex.load(settings, embeddings_path)`. Kiểm tra `persist_path` trong manifest cho thấy đường dẫn vẫn trỏ về vị trí cũ.
- **Nguyên nhân gốc:** `LocalEmbeddingIndex.build()` lưu `persist_path.resolve()` trực tiếp vào manifest. Absolute path phụ thuộc máy và vị trí checkout, trong khi manifest cần là artifact portable để toàn nhóm có thể chạy cùng một project.
- **Cách xử lý:** Thêm `_manifest_persist_path()` để ưu tiên lưu path tương đối `data/chroma`. Thêm `_resolve_persist_path()` để resolve path tương đối từ project root, từ chối absolute path nằm ngoài project hiện tại và fallback về `settings.paths.chroma_dir`. Sau đó build lại ba manifests baseline, corrupted và repaired.
- **Cách xác minh sau khi sửa:** Cả ba manifests có `persist_path: "data/chroma"`; `LocalEmbeddingIndex.load()` load thành công `papers-baseline`, `papers-corrupted` và `papers-repaired`; mỗi collection có 24 documents và semantic query trả đủ top 4 results. Ba CP6 collection checks đều PASS.
- **Điều học được:** Artifact của vector index phải portable và không được phụ thuộc vào filesystem layout của một máy cụ thể. Path resolution cần được coi là một phần của data/index contract, không chỉ là chi tiết cấu hình.

## 7. Hiểu biết về luồng end-to-end

1. **Crossref đến vector index:** Role 2 lưu raw response và parse thành `PaperRecord`. Role 3 normalize/dedupe, tính `age_days` và tạo `text_for_embedding`. Role 4 embed text bằng MiniLM, ghi vectors cùng metadata vào Chroma và lưu manifest để load lại.
2. **Evaluation set và ground-truth IDs:** Test set gồm question, ground truth và `ground_truth_doc_ids` lấy từ clean `paper_id`. Evaluator so IDs retrieved trong top 4 với ground-truth IDs để tính `retrieval_hit_rate`, đồng thời so answer với ground truth bằng Token F1 và LLM judge.
3. **Quality và freshness:** Quality checks đo completeness, uniqueness và validity như ID/title/summary không rỗng, ID không trùng, `age_days` hợp lệ. Freshness monitoring tập trung vào publication date, stale rows và freshness threshold 180 ngày.
4. **Cùng test set:** Nếu thay test set giữa các trạng thái, delta có thể do câu hỏi thay đổi. Khóa cùng test set và hash giúp cô lập data state là biến chính của thí nghiệm.
5. **Repair thành công:** Repaired clean phải được build lại từ raw snapshot, schema/quality/freshness phải phục hồi và metrics trên cùng test set phải trở về baseline. CP6 xác nhận clean repaired khớp baseline, affected records được phục hồi và metric deltas đều bằng 0.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 1.0000 | 1.0000 | Ground-truth document vẫn nằm trong top 4; hit rate không đủ để phát hiện content degradation |
| `mean_token_f1` | 1.0000 | 0.8414 | 1.0000 | Corrupted content làm answer mất token đúng; repair phục hồi hoàn toàn |
| `judge_accuracy` | 0.9583 | 0.7917 | 0.9583 | LLM judge phát hiện answer quality giảm dù retrieval hit không đổi |
| `mean_judge_score` | 4.8333 | 4.2500 | 4.8333 | Giảm 0.5833 rồi phục hồi về baseline |
| Quality checks | 8/8 PASS | 5/8 PASS | 8/8 PASS | Corrupted FAIL ở uniqueness, summary completeness và freshness |
| Freshness status | FRESH | STALE/INVALID | FRESH | Publication date bị lùi 730 ngày tạo 1 stale row |

### Kết luận từ số liệu

1. `blank_summary` → quality check summary FAIL → `q-01-summary` vẫn retrieval hit nhưng answer rỗng, Token F1 giảm 1.0 → 0.0 và judge score giảm 5 → 2.
2. `truncate_title` → exact title trong locked question không còn khớp indexed title → ground-truth paper vẫn ở top 4 nhưng paper khác lên rank đầu, làm summary/authors answers giảm điểm.
3. Repair từ raw snapshot → quality/freshness chuyển PASS/FRESH trở lại → `mean_token_f1`, `judge_accuracy` và `mean_judge_score` phục hồi đúng baseline.

Corruption ảnh hưởng rõ nhất có bằng chứng trực tiếp là `blank_summary`: document vẫn được retrieve nhưng thiếu nội dung cần thiết để tạo câu trả lời. Điều này cho thấy “retrieve đúng document” khác với “document còn usable”. `stale_publication_date` cũng có quan hệ rõ giữa corruption log, freshness alert và answer date sai.

Kết quả khác kỳ vọng ban đầu là `retrieval_hit_rate` không giảm. Kiểm tra case-level cho thấy metric chỉ yêu cầu ground-truth document xuất hiện ở bất kỳ vị trí nào trong top 4, trong khi QA dùng result đầu tiên hoặc exact lookup. Vì vậy ranking/content có thể xấu đi mà hit rate vẫn 1.0. Kết luận phù hợp là cần theo dõi đồng thời retrieval ranking, answer metrics và data quality signals.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. RAG index phải có portable manifest, stable document ID và collection isolation; nếu không, kết quả rất dễ phụ thuộc máy hoặc thứ tự chạy.
2. Data observability phải đo cả quality/freshness và liên kết signal với case-level answer evidence; chỉ nhìn row count hoặc script exit code là chưa đủ.
3. `retrieval_hit_rate=1.0` không đảm bảo agent trả lời đúng. Corrupted title/summary/date có thể làm top answer sai hoặc rỗng dù ground-truth document vẫn trong top-k.

### Nếu có thêm thời gian

Tôi sẽ thêm hybrid retrieval (dense MiniLM + BM25) và reranker, nhưng giữ nguyên corpus, test set, `top_k` và evaluator để comparison công bằng. Thí nghiệm sẽ đo Recall@k, MRR/nDCG, Token F1, judge metrics và latency; chỉ kết luận cải thiện khi retrieval ranking và answer quality tăng mà latency/cost vẫn chấp nhận được.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng vai trò, artifacts và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module RAG.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Hà Bảo Long  
**Ngày xác nhận:** 2026-08-06
