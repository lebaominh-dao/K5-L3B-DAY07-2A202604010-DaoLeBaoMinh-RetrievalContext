# Báo cáo Day 7 — Đào Lê Bảo Minh (2A202604010)

Agent `claude-haiku-5-5` tìm bằng chứng trong kho Day 6, trả lời có citation hoặc từ chối khi thiếu bằng chứng. Chi tiết thí nghiệm: [experiments/dev_experiments.md](../../experiments/dev_experiments.md). Code và thí nghiệm làm cùng trợ lý AI (Claude Code); tác giả kiểm tra kết quả và tự chấm toàn bộ nhãn.

## Dữ liệu và benchmark

- **Nguồn:** OpenStax *Psychology 2e* (CC BY 4.0), chương 6 và 8, 52 trang; 256 chunk theo đoạn (cấu hình B của Day 6, tối đa 1.000 ký tự).
- **Vector store, embedding:** PostgreSQL 16.16 + pgvector 0.8.7 (Day 6); `openai/text-embedding-3-small` qua OpenRouter, 1.536 chiều; query embedding cùng model.
- **Agent, dev/test:** `claude-haiku-5-5`, effort `medium`. Benchmark 39 câu: dev 25 có đáp án + 6 thiếu evidence, test 5 + 3. Câu D01–D15, T16–T20 lấy từ Day 6; D16–D25, DA4–DA6 thêm vào dev ở vòng 2 từ chunk chọn ngẫu nhiên (seed cố định, loại trang chứa gold của test), viết mà không xem kết quả retrieval ([benchmark/](../../benchmark/README.md)).
- **Có/thiếu evidence, cách chấm:** câu có đáp án ghi nguồn, trang và câu evidence nằm trọn trong một chunk. Câu thiếu evidence gần chủ đề, vắng mặt được kiểm tra bằng từ khóa trên chunk và PDF; có câu bẫy (TA1: "blocking" ở chương 8 mang nghĩa khác). Hit = đúng nguồn, đúng trang, chứa trọn evidence. Chấm tay theo BENCHMARK.md.

## Retrieval và thử nghiệm

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | Dense (pgvector), top-3, filter chapter | Phương pháp bắt buộc | dev | 17/25 | 22/25 | 22/25 | 758 ms; ~$0 |
| Phương pháp 2 | BM25 (k1 1,5, b 0,75), top-3 | Câu trùng từ khóa với sách | dev | 18/25 | 21/25 | 21/25 | 0,4 ms; $0 |
| Phương pháp 3 | Hybrid RRF dense + BM25 (k = 60), top-3 | Hai nhánh bù nhau | dev | 17/25 | **24/25** | **24/25** | 736 ms; ~$0 |
| Agent A0 | Agent + hybrid, top-3, 4 search, 4.000 ký tự | Cấu hình mặc định | dev | 17/25 | 24/25 | 23,0/25 | 4,89 s; $0,00056/câu |
| Cải thiện 1: C1 | A0 nhưng top-5, 6.000 ký tự | Evidence hạng 4–5 vào được context | dev | 17/25 | 24/25 | **25,0/25** | 4,79 s; $0,00060/câu |
| Cải thiện 2: C2 | A0 nhưng effort `low` | Rẻ hơn, giữ chất lượng | dev | 17/25 | 24/25 | 22,5/25 | 4,67 s; $0,00049/câu |
| Cấu hình đã chọn (C1) | hybrid, top-5, 6.000 ký tự | Chốt trên dev | test | 5/5 | 5/5 | 5/5 | 5,29 s; $0,0058/8 câu |
| Baseline (A0) | hybrid, top-3, 4.000 ký tự | | test | 5/5 | 5/5 | 5/5 | 5,03 s; $0,0048/8 câu |

Hit@1/Hit@3 là xếp hạng trên câu hỏi gốc (agent dùng hybrid nên lấy số của hybrid); Context Evidence Rate của agent là trung bình 2 lần chạy. Thêm C3 (agent + dense): 22,0/25. TF-IDF của starter: 14/25, 20/25. Thời gian dense/hybrid chủ yếu là gọi API embedding (~730 ms).

**Hai lỗi dev:**

1. **D09, D17:** evidence ở hạng 4–5, top-3 không lấy được dù agent search lại. Lấy thêm chunk liền kề không giúp (thử offline); top-5 (C1) sửa được ở 4/4 lần chạy. D17 là câu chọn ngẫu nhiên, nên đây là xác nhận độc lập.
2. **D07, D08:** lỗi harness. Model chép sai chunk ID dài và chèn markup vào câu trả lời, nên câu đúng bị tính là từ chối. Sửa bằng nhãn ngắn `S1, S2…` và lấy citation từ nội dung câu trả lời: từ chối nhầm giảm từ 2/15 xuống 0/15.

**Chọn cấu hình:** vòng 1 (15 câu dev) không chốt được vì chỉ D09 phân biệt các cấu hình và hai tiêu chí viết trước mâu thuẫn. Vòng 2 dùng tiêu chí ghi trước khi chạy: điểm = Context evidence + citation chứa evidence + từ chối đúng (tối đa 56), phải hơn A0 quá 1,5 điểm. Kết quả: A0 52, **C1 56**, C2 51, C3 50 → chọn C1. Đánh đổi: token +10%, chi phí +7%, thời gian tương đương.

## Agent và đánh giá

- **Thiết kế:** vòng lặp tool use viết tay ([src/agent.py](../../src/agent.py)) với `search_corpus` và `submit_answer`. Context gộp qua các lần search, bỏ trùng, giới hạn theo số ký tự. Citation chỉ hợp lệ khi trỏ vào context; trả lời mà không có citation hợp lệ thì tính là từ chối. Dừng khi gọi `submit_answer`, tối đa 4 search và 8 lần gọi model. Lỗi API được ghi là `error`.

| Cấu hình / split | Tool use | Search/câu | Grounded answer 0/1/2, TB | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| A0 / dev (2 lần) | 31/31 | 1,79 | không chấm tay | không chấm tay | 24/24, 25/25 | 6/6 | 1/25, 0/25 |
| C1 / dev (2 lần) | 31/31 | 1,65 | không chấm tay | không chấm tay | 25/25 | 6/6 | 0/25 |
| A0 / test | 8/8 | 1,75 | 0/0/5, **2,0** | 8/9 | 5/5 | 3/3 | 0/5 |
| C1 / test | 8/8 | 2,12 | 0/2/3, **1,6** | 7/7 | 5/5 | 3/3 | 0/5 |

Context chấm tay: 5/5 câu mức 2 ở cả hai. Câu không đạt tối đa, theo ghi chú người chấm:

- A0 T19, citation `p274:c003`: “Trích dẫn p274:c003 không liên quan đến câu trả lời…”
- C1 T17 (1 điểm): “đúng ý là "trí nhớ sợ hãi phai nhạt dần" nhưng không nói điều đó thay đổi hành vi của chuột như thế nào”
- C1 T20 (1 điểm): “agent không giải thích bối cảnh cú sốc điện được tạo ra (khi con chó lại gần mép sân)”

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| T19 (C1) | Có đáp án | 2 search, đều trả `p274:c003`, `p274:c004` | "smashed" làm ước lượng tốc độ cao hơn, một tuần sau nhớ nhầm có kính vỡ; trích c003, c004 | Trả lời 2, context 2, citation 2/2 |
| TA1 (C1) | Thiếu evidence, bẫy | 4 search; lần cuối trả các đoạn "blocking" của chương 8 | "The textbook passages… do not cover Kamin's blocking effect", không citation | Từ chối đúng; không dùng nghĩa sai để trả lời |
| D09 (A0, dev) | Có đáp án | 3 search top-3, không có chunk evidence `p211:c002` | Từ chối | Lỗi: thiếu evidence trong context. C1 lấy được ở hạng 5 và trả lời đúng |

- **Trace, nhãn, lệnh chạy:** `starter/results/` gồm `retrieval-dev`, `retrieval-test`, `dev-exp`, `dev-exp2` và `agent-test-{A0,C1}` (trace, `reviews.json`, `agent_metrics.json`). Lệnh chạy ở [README](../../README.md). Tổng chi phí Claude + embedding khoảng $0,24.
- **Kết quả, đánh đổi, giới hạn:**
  - Trên dev, C1 sửa D09/D17 và không làm giảm khả năng từ chối.
  - Trên test, cả hai cấu hình đều đạt tối đa ở mọi metric tự động: test nhỏ và dễ, không câu nào có evidence ở hạng 4–5. C1 tốn thêm 19% chi phí. Chấm tay cho C1 thấp hơn ở T17 và T20 theo ghi chú trên.
  - Giới hạn: test chỉ 8 câu; câu hỏi do AI soạn; mỗi câu chỉ có một evidence, chưa có multi-hop; gold không liệt kê hết các đoạn hỗ trợ hợp lệ (ví dụ D19); một người chấm; model không tất định.

## Thử thách nâng cao (nếu thực hiện)

Không thực hiện.
