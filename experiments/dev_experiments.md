# Thử nghiệm cải thiện trên dev

Chỉ dùng dev (15 câu có đáp án D01–D15, 3 câu thiếu evidence DA1–DA3). Không chạy test cho tới khi chốt cấu hình ở cuối file này.

## Kế hoạch (ghi trước khi chạy)

### Baseline A0

Agent `claude-haiku-5-5`, effort `medium`, retriever `hybrid` (RRF dense + BM25), top-3 mỗi lần search, tối đa 4 lần search, context budget 4.000 ký tự. Lần chạy dev đầu tiên (sau khi sửa harness, xem [src/README.md](../src/README.md#lỗi-dev-đã-sửa-ở-harness)): Context Evidence 14/15, citation chứa evidence 14/15, từ chối đúng 3/3, từ chối nhầm 0/15, khoảng $0,010 cho 18 câu.

### Phân tích lỗi trước khi thử

| Câu | Lỗi | Nguyên nhân | Hướng thử |
|---|---|---|---|
| D09 | Evidence không vào context sau 3 lần search; agent trả lời "đoạn văn không nói" | Chunk evidence `p211:c002` nằm ở hạng 4 (dense) / 5 (hybrid) của câu hỏi gốc; các query agent tự viết lại cũng chỉ trả về chunk cùng chủ đề ở top-3 | Tăng top-k (C1) |
| D09 | (đã loại) lấy chunk liền kề ±1 của top-3 | Kiểm tra offline: `p211:c002` cách chunk gần nhất trong top-3 (`p211:c000`) 2 vị trí, nên ±1 không với tới; không câu dev nào khác cần | Không chạy |
| D07, D08 | Bị tính là từ chối dù trả lời đúng | Lỗi harness (chép sai chunk ID dài; model chèn markup vào trường answer) | Đã sửa trước baseline |
| DA2, DA3 | Budget cắt 6 và 1 chunk | Agent search 3–4 lần vì không tìm thấy; context đầy | Theo dõi, không phải lỗi chất lượng |

### Cấu hình thử

| ID | Thay đổi so với A0 | Giả thuyết | Rủi ro |
|---|---|---|---|
| C1 | top-k 5, budget 6.000 | D09 có evidence trong context; các câu khác giữ nguyên | Nhiều token hơn; nhiều đoạn gây nhiễu, có thể làm câu thiếu evidence bị trả lời |
| C2 | effort `low` | Chất lượng giữ nguyên với câu hỏi một bước, ít token output và nhanh hơn | Ít search lại hơn, có thể giảm từ chối đúng |
| C3 | retriever `dense` thay `hybrid` | Ở bước 1 hybrid hơn dense ở Evidence Hit@3 (14 vs 13/15, khác ở D05); kiểm tra xem agent search lại có bù được không | D05 mất evidence |

Mỗi cấu hình chạy 2 lần (model không tất định); báo cả hai lần.

### Tiêu chí chọn (chốt trước khi chạy)

1. **Ràng buộc:** từ chối đúng 3/3 ở cả hai lần chạy và từ chối nhầm ≤ 1/15 mỗi lần; không có lỗi `error`. Cấu hình vi phạm bị loại.
2. **Chất lượng:** Context Evidence Rate trung bình hai lần, rồi citation chứa evidence (proxy tự động) trung bình hai lần.
3. **Chênh ≤ 1 câu được coi là hòa** (1 câu = 6,7 điểm phần trăm trên 15 câu, nằm trong dao động giữa hai lần chạy).
4. Hòa thì chọn cấu hình rẻ hơn (chi phí/câu), rồi nhanh hơn (trung vị giây/câu).
5. Nếu không cấu hình nào hơn A0 quá ngưỡng hòa, giữ A0.

## Kết quả (chạy ngày 2026-11-16, mỗi cấu hình 2 lần, 18 câu dev)

| Config | Thiết lập | Context evidence (TB) | Citation chứa evidence (TB) | Từ chối đúng (min) | Từ chối nhầm (max) | Lỗi | Search/câu | Trung vị s/câu | Token/câu | $/câu |
|---|---|---|---|---|---|---|---|---|---|---|
| A0 | hybrid, top-3, 4.000 ký tự, effort medium | 14,0/15 | 14,0/15 | 3/3 | 1/15 | 0 | 1,78 | 4,70 | 4.351 | 0,00058 |
| C1 | hybrid, top-5, 6.000 ký tự, effort medium | 15,0/15 | 15,0/15 | 3/3 | 0/15 | 0 | 1,58 | 4,95 | 4.578 | 0,00060 |
| C2 | hybrid, top-3, 4.000 ký tự, effort low | 14,0/15 | 14,0/15 | 3/3 | 1/15 | 0 | 1,47 | 4,58 | 3.777 | 0,00050 |
| C3 | dense, top-3, 4.000 ký tự, effort medium | 14,5/15 | 14,5/15 | 3/3 | 1/15 | 0 | 1,67 | 4,67 | 4.067 | 0,00054 |

Từng lần chạy và câu trượt: `starter/results/dev-exp/comparison.md`; trace đầy đủ: `starter/results/dev-exp/<config>-r<n>/traces.json`. Các câu ngoài D09 giống nhau ở mọi lần chạy về Context evidence và citation.

### Đối chiếu giả thuyết

- **C1 (top-5): đúng giả thuyết.** D09 có evidence trong context và được trả lời đúng, trích `p211:c002`, ở cả 2/2 lần; không câu nào khác thay đổi; câu thiếu evidence vẫn bị từ chối 3/3. Search ít hơn (1,58 so với 1,78/câu) vì lần đầu đã đủ evidence; token +5%, chi phí +3%, chậm hơn 0,25 s.
- **C2 (effort low): đúng giả thuyết.** Chất lượng như A0 (14/15, cùng trượt D09), từ chối đúng 3/3; ít token hơn 13%, rẻ hơn 14%, search ít hơn; câu trả lời ngắn hơn một chút (trung vị 328 so với 358 ký tự).
- **C3 (dense): không rõ.** D05 không bị mất evidence (agent search lại bù được); D09 lúc có lúc không (r2 có vì dense xếp `p211:c002` hạng 4, gần top-3 hơn hybrid). Không khác A0 quá ngưỡng hòa.
- **Dao động giữa hai lần chạy:** chỉ ở D09 (A0-r2, C2-r2, C3-r1 từ chối D09 vì context thiếu evidence; các lần khác trả lời rằng đoạn văn không nói). Không có lỗi API nào.

### Áp tiêu chí

Mọi cấu hình qua ràng buộc (từ chối đúng 3/3, từ chối nhầm ≤ 1, không lỗi). Về chất lượng, C1 hơn A0 đúng 1 câu (D09), tức **nằm trong ngưỡng hòa** của tiêu chí 3. Tiêu chí 4 (hòa thì chọn rẻ hơn, sẽ là C2) và tiêu chí 5 (không ai hơn A0 quá ngưỡng thì giữ A0) mâu thuẫn nhau trong tình huống này; đây là sơ suất khi viết tiêu chí, ghi lại ở đây thay vì sửa tiêu chí sau khi xem kết quả.

Vòng 1 không chốt cấu hình: dev quá nhỏ (chỉ D09 phân biệt) và tiêu chí 4/5 mâu thuẫn. Chuyển sang vòng 2.

## Vòng 2: dev mở rộng (ghi trước khi chạy)

Dev thêm D16–D25 (10 câu có đáp án) và DA4–DA6 (3 câu thiếu evidence kiểu gần trúng), tạo theo quy trình ngẫu nhiên cố định không nhìn kết quả retrieval ([benchmark/README.md](../benchmark/README.md#mở-rộng-dev-vòng-2)). Dev vòng 2: 25 câu có đáp án, 6 câu thiếu evidence. Test không đổi, chưa chạy.

Chạy lại đúng 4 cấu hình A0, C1, C2, C3 như vòng 1, mỗi cấu hình 2 lần, trên toàn bộ dev vòng 2 (31 câu). Kết quả vòng 1 không dùng để chọn.

### Tiêu chí chọn vòng 2 (thay tiêu chí vòng 1, chốt trước khi chạy)

1. **Ràng buộc:** từ chối đúng ≥ 5/6 ở cả hai lần chạy; từ chối nhầm ≤ 2/25 mỗi lần; không có lỗi `error`. Vi phạm thì loại.
2. **Điểm chất lượng** = trung bình hai lần của (Context evidence + citation chứa evidence + số câu thiếu evidence từ chối đúng), tối đa 25 + 25 + 6 = 56.
3. **Hơn A0** nghĩa là điểm chất lượng cao hơn A0 **quá 1,5** (chênh lệch nhỏ hơn coi là dao động).
4. Nếu không cấu hình nào hơn A0, **chốt A0**. Nếu có, chọn cấu hình điểm cao nhất trong số đó; bằng điểm thì chọn rẻ hơn ($/câu), rồi nhanh hơn.
5. Ghi riêng đánh đổi: token, chi phí, thời gian của cấu hình chọn so với A0.

### Kết quả vòng 2 (2026-11-16, mỗi cấu hình 2 lần, 31 câu dev)

| Config | Context evidence (TB) | Citation chứa evidence (TB) | Từ chối đúng (min) | Từ chối nhầm (max) | Lỗi | **Điểm chất lượng** (TB, /56) | Search/câu | Trung vị s/câu | Token/câu | $/câu |
|---|---|---|---|---|---|---|---|---|---|---|
| A0 | 23,0/25 | 23,0/25 | 6/6 | 1/25 | 0 | **52,0** (52, 52) | 1,79 | 4,89 | 4.145 | 0,00056 |
| C1 | 25,0/25 | 25,0/25 | 6/6 | 0/25 | 0 | **56,0** (56, 56) | 1,65 | 4,79 | 4.556 | 0,00060 |
| C2 | 22,5/25 | 22,5/25 | 6/6 | 0/25 | 0 | **51,0** (52, 50) | 1,45 | 4,67 | 3.584 | 0,00049 |
| C3 | 22,0/25 | 22,0/25 | 6/6 | 1/25 | 0 | **50,0** (50, 50) | 1,82 | 5,01 | 4.309 | 0,00058 |

Từng lần chạy: `starter/results/dev-exp2/comparison.md`; trace: `starter/results/dev-exp2/<config>-r<n>/traces.json`.

### Phân tích lỗi vòng 2

- **D09 và D17: cùng một cơ chế.** Evidence nằm ở chunk hạng 4–5 (D09: `p211:c002`; D17: `p212:c001`); với top-3, các query agent viết lại chỉ trả về chunk cùng chủ đề (`p211:c005`, `p210:c002`), nên agent trả lời bằng nguyên lý chung hoặc từ chối. Top-5 đưa đúng chunk vào ngay lần search đầu ở cả 4/4 lần chạy C1. D17 thuộc nhóm câu chọn ngẫu nhiên ở vòng 2, nên đây là xác nhận độc lập cho giả thuyết C1, không phải câu viết riêng cho C1.
- **D19 (C2-r2, C3): hạn chế của chấm tự động, không phải lỗi trả lời.** Agent trả lời đúng ("elaborative rehearsal… relating it to knowledge already stored") nhưng dùng đoạn định nghĩa ở tr. 261/281 thay vì ví dụ ở tr. 263 trong gold. Gold chỉ có một evidence, nên metric tự động tính là thiếu. Cần chấm tay; không sửa gold sau khi xem kết quả.
- **Câu thiếu evidence:** mọi cấu hình từ chối đúng 6/6 ở mọi lần chạy, kể cả 3 câu gần trúng mới (DA4–DA6). Rủi ro "top-5 thêm đoạn nhiễu khiến trả lời bừa" của C1 không xảy ra trên dev.
- **C2 (effort low):** rẻ nhất (−12% so với A0) nhưng không hơn về chất lượng; **C3 (dense):** thấp nhất, cùng trượt D09/D17/D19.

### Áp tiêu chí vòng 2

Mọi cấu hình qua ràng buộc. Chỉ C1 hơn A0 quá ngưỡng 1,5 (56,0 so với 52,0, chênh 4,0; ổn định 56 ở cả hai lần). Theo tiêu chí 4: **chọn C1**.

Đánh đổi so với A0: token +10% (4.556 so với 4.145/câu), chi phí +7% ($0,00060 so với $0,00056/câu, tức khoảng $0,019 cho 31 câu), thời gian tương đương (4,79 so với 4,89 s trung vị), ít search hơn (1,65 so với 1,79/câu) vì lần đầu thường đã đủ evidence.

## Cấu hình chốt

**C1:** `claude-haiku-5-5`, effort `medium`, retriever `hybrid` (RRF dense + BM25, k = 60, 20 candidate mỗi nhánh), **top-5** mỗi lần search, tối đa 4 lần search, context budget **6.000 ký tự**.

```bash
.venv/bin/python src/run_agent.py --split test --top-k 5 --budget 6000 --output starter/results/agent-test-C1
.venv/bin/python src/run_agent.py --split test --output starter/results/agent-test-A0   # baseline
```

Chốt ngày 2026-11-16, trước khi chạy bất kỳ câu test nào. Sau khi chạy test, không đổi cấu hình dựa trên kết quả test.
