# Benchmark Day 7

Corpus: OpenStax *Psychology 2e*, chương 6 (Learning, tr. 193–218) và chương 8 (Memory, tr. 259–284), số trang theo PDF; giấy phép CC BY 4.0. Chunk là cấu hình B của Day 6 (256 chunk theo đoạn, tối đa 1.000 ký tự), export bằng [src/day6_export.py](../src/day6_export.py).

| Loại câu | Dev | Test | File |
|---|---:|---:|---|
| Có đáp án | 15 (D01–D15) | 5 (T16–T20) | `questions.json` |
| Thiếu bằng chứng | 3 (DA1–DA3) | 3 (TA1–TA3) | `abstain_cases.json` |
| **Tổng** | **18** | **8** | `cases.json` (26 câu) |

## Câu có đáp án

Lấy nguyên từ benchmark Day 6 (AI soạn sau khi đọc corpus, tác giả kiểm tra), chuyển sang schema Day 7. Mỗi câu có `gold` gồm nguồn, trang và evidence; D05 có 2 evidence thay thế (tr. 197 và 198). 4 câu có `filter` `{"chapter": N}` (D02, D15, T17, T20): đây là thông tin người dùng cung cấp trước, không suy ra từ gold.

## Câu thiếu bằng chứng

Mỗi câu gần chủ đề của corpus và có `absence_reason`. Một số câu cố ý đặt bẫy:

- **DA1** (năm Pavlov nhận Nobel): Pavlov có trong chương 6 nhưng không có Nobel, nên model dễ trả lời bằng kiến thức có sẵn.
- **TA1** (blocking của Kamin): chữ "blocking" có trong chương 8 nhưng mang nghĩa khác (quên kiểu "đầu lưỡi"), nên lexical retrieval dễ trả về sai khái niệm.

Cách kiểm tra: tìm mọi từ khóa trong `absence_check.terms` (không phân biệt hoa thường) trên toàn bộ 256 chunk và trên text từng trang PDF của 52 trang corpus; không có kết quả nào. `near_topic_terms` phải xuất hiện ít nhất một lần để chứng tỏ câu hỏi gần chủ đề. `src/build_benchmark.py` chạy lại phần kiểm tra trên chunk.

## Tách dev/test

Split giữ nguyên từ Day 6 và đã cố định trước khi chạy Day 7. Ở Day 6, T16–T20 có chạy evaluate một lần cùng lúc với dev nhưng không dùng để chỉnh tham số (xem báo cáo Day 6). Ở Day 7, không xem kết quả test cho tới khi chốt cấu hình trên dev.

## Dùng khi chạy

`cases.json` chỉ chứa thông tin agent được thấy (`id`, `split`, `question`, `filter`) cùng `answerable` / `expected_behavior` cho `starter/agent_metrics.py`. Không đưa `gold`, `expected_answer`, `absence_reason` hay `absence_check` vào agent hoặc retrieval.

Dựng lại và kiểm tra (cần `starter/data/day6/chunks.json` từ bước export):

```bash
python3 src/build_benchmark.py --chunks starter/data/day6/chunks.json
```

## Giới hạn

- Kiểm tra vắng mặt dựa trên từ khóa: chứng minh các thuật ngữ đó không xuất hiện, nhưng không loại trừ hoàn toàn trường hợp corpus diễn đạt ý tương tự bằng từ khác. Cần đọc lại khi chấm.
- Test nhỏ (5 câu có đáp án, 3 câu thiếu bằng chứng): mỗi câu thay đổi tỷ lệ 20 hoặc 33 điểm phần trăm.
