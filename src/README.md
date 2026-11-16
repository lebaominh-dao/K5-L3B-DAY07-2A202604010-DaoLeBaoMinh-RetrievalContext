# Code

Đặt code của bạn tại đây hoặc mở rộng [starter](../starter/README.md). Khung agent chưa kết nối model và vector store thật.

## Export dữ liệu Day 6

`day6_export.py` đọc bảng `chunks` trong pgvector của Day 6 và file `benchmark/questions.json`, rồi ghi ra theo [định dạng Day 7](../data/README.md). So với `starter/convert_day6.py`, script xử lý thêm:

- chép `chapter` và `section` (cột riêng trong bảng Day 6) vào `metadata`, để filter `{"chapter": N}` của benchmark vẫn dùng được;
- nhận file câu hỏi dạng `{meta, questions}` lẫn dạng JSON array;
- giữ `alt_gold` (evidence thay thế, ví dụ D05) bằng cách thêm vào `gold`.

Cuối cùng, script kiểm tra bằng `starter/baseline.validate`: mỗi evidence phải nằm trọn trong một chunk đúng nguồn và trang, sai là dừng.

Cần container Postgres của Day 6 đang chạy (`docker compose -p day6_student_starter up -d --wait` trong `Day06/starter`). Chạy từ thư mục gốc Day 7:

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
export $(grep '^DATABASE_URL=' ../Day06/starter/.env)
.venv/bin/python src/day6_export.py --questions ../Day06/benchmark/questions.json --strategy B --output starter/data/day6
```

Kết quả gồm `chunks.json`, `questions.json` và `export_meta.json` (cấu hình, số chiều embedding, số chunk/câu). Dùng cấu hình B: C có cùng chunk với B (filter `chapter` đã nằm trong `metadata`), còn A chunk cố định 500 ký tự nên evidence của D15 bị cắt qua hai chunk và không qua bước kiểm tra.

## Retrieval

[retrieval.py](retrieval.py) có 4 retriever chung interface `search(query, *, filters=None, top_k=3)`, trả chunk Day 7 kèm `score`, `rank`, `method`. Lỗi database/API được raise, không thay bằng kết quả rỗng.

| Method | Cách tìm | Cấu hình |
|---|---|---|
| `dense` | Query embedding `openai/text-embedding-3-small` (OpenRouter, 1536 chiều) + cosine trên pgvector Day 6, filter bằng cột `chapter`/`section` | strategy B |
| `bm25` | Okapi BM25 trên 256 chunk export, cùng tokenizer với TF-IDF | k1 = 1.5, b = 0.75 |
| `tfidf` | Baseline TF-IDF của starter (mốc so sánh) | mặc định starter |
| `hybrid` | Reciprocal Rank Fusion của dense + BM25: score = Σ 1/(60 + rank), không cộng score thô | 20 candidate mỗi nhánh |

Filter (`{"chapter": N}`) lấy từ input câu hỏi, áp dụng trước khi xếp hạng ở mọi method.

Chạy benchmark (chỉ load câu của split được chọn; chạy `--split test` sau khi đã chốt cấu hình trên dev):

```bash
.venv/bin/python src/run_retrieval.py --split dev --output starter/results/retrieval-dev
```

Kết quả: `summary.json` (cấu hình + metrics), `traces.json` (top-10 từng câu với score/rank/hit, top-3 của câu thiếu evidence), `comparison.md` (bảng so sánh). Metric dùng cùng định nghĩa hit với `starter/baseline.hit`; Context Evidence Rate đóng gói top-3 vào 3.000 ký tự (`--budget`).

## Agent

[agent.py](agent.py) là vòng lặp tool use viết tay với `claude-haiku-5-5` (Anthropic SDK). Viết tay thay vì dùng tool runner để giới hạn số lần search, ghi trace từng lượt và đóng gói context theo ngân sách ký tự.

- **Tool:** `search_corpus(query)` gọi retriever đã chọn (mặc định `hybrid`, top-3); `submit_answer(status, answer, citations)` kết thúc lượt chạy. Cả hai dùng `strict: true`. Filter `chapter` lấy từ input của câu hỏi, model không tự chọn.
- **Context:** gộp kết quả qua các lượt search, bỏ chunk trùng, giữ chunk cũ trước, dừng khi vượt 4.000 ký tự (`pack_context` của starter). Mỗi đoạn được gắn nhãn ngắn `S1`, `S2`…; câu trả lời trích bằng nhãn, sau đó nhãn được đổi lại thành chunk ID thật.
- **Citation:** chỉ tính nhãn xuất hiện trong câu trả lời **và** trỏ vào context cuối. Trả lời mà không có citation hợp lệ thì bị chuyển thành từ chối (giống starter).
- **Điều kiện dừng:** model gọi `submit_answer`; quá `--max-searches` (mặc định 4) thì lần search tiếp theo nhận lỗi và lời nhắc trả lời; trả lời bằng text mà không gọi tool thì được nhắc một lần, lần hai ghi `error`; tối đa 8 lần gọi model. Lỗi API/vector store và `stop_reason` `refusal`/`max_tokens` được ghi là `error`, không thay bằng câu trả lời giả.

Chạy trên một split (agent chỉ đọc `benchmark/cases.json`; gold của split đó chỉ được đọc sau khi chạy xong để chấm tự động):

```bash
.venv/bin/python src/run_agent.py --split dev --output starter/results/agent-dev
```

Tham số: `--retriever`, `--effort` (mặc định `medium`), `--top-k`, `--max-searches`, `--budget`, `--ids` (chạy một vài câu). Kết quả: `traces.json` (mọi lượt search, context, câu trả lời, citation, token, chi phí, thời gian; dùng được với `starter/agent_metrics.py`), `summary.json` (metric tự động) và `reviews_template.json` (khung nhãn chấm tay).

Metric tự động: tool use, phân bố số lần search, Context Evidence Rate, citation chứa gold evidence (proxy, vẫn phải chấm tay), tỷ lệ từ chối đúng/nhầm, lỗi, thời gian, token, chi phí.

### Lỗi dev đã sửa ở harness

Lần chạy dev đầu tiên có 2 câu có đáp án bị tính là từ chối dù model trả lời đúng:

- **D07:** model chép chunk ID dài (`B:psych2e-ch6:p206:c005`) thiếu tiền tố `B:` trong câu trả lời, nên bước kiểm tra `[id]` không khớp. Sửa: dùng nhãn ngắn `S1`, `S2`….
- **D08:** Haiku chèn markup `</answer><parameter name="citations">…` vào trường `answer`, còn trường `citations` rỗng. Sửa: lấy citation từ nhãn trong câu trả lời và cắt phần markup bị lẫn (ghi event `leaked_markup_removed`).

Trước khi sửa: từ chối nhầm 2/15, citation chứa evidence 12/15. Sau khi sửa: 0/15 và 14/15.
