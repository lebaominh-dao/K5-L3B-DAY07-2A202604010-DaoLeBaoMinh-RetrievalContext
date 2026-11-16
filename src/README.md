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
