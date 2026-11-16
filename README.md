# Day 7 — Agentic RAG

## Bài làm (Đào Lê Bảo Minh · 2A202604010)

Agent `claude-haiku-5-5` tìm bằng chứng trong kho Day 6 (OpenStax *Psychology 2e*, chương 6 và 8, CC BY 4.0; 256 chunk theo đoạn, `openai/text-embedding-3-small` 1536 chiều trên PostgreSQL 16 + pgvector 0.8.7), trả lời có citation hoặc từ chối khi thiếu evidence. Cấu hình chốt trên dev: **hybrid RRF (dense + BM25), top-5, context 6.000 ký tự, tối đa 4 lần search**.

| Nội dung | Đường dẫn |
|---|---|
| Báo cáo cá nhân | [report/individual/2A202604010_DaoLeBaoMinh.md](report/individual/2A202604010_DaoLeBaoMinh.md) |
| Code: export Day 6, retrieval, agent, đánh giá, công cụ chấm | [src/](src/README.md) |
| Benchmark 39 câu (dev 25 + 6 thiếu evidence, test 5 + 3) | [benchmark/](benchmark/README.md) |
| Kế hoạch, tiêu chí chọn, kết quả dev/test, nhãn chấm tay | [experiments/dev_experiments.md](experiments/dev_experiments.md) |
| Trace, metrics, nhãn | [starter/results/](starter/results/) (`retrieval-dev`, `retrieval-test`, `dev-exp`, `dev-exp2`, `agent-test-A0`, `agent-test-C1`) |
| Test | [tests/](tests/) |

### Setup và chạy

Cần Day 6 đã ingest (container `day6_student_starter` đang chạy, xem README Day 6), Python 3.11+ và [uv](https://docs.astral.sh/uv/).

```bash
uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env    # điền OPENROUTER_API_KEY, ANTHROPIC_API_KEY (ROUTEAPI_API_KEY chỉ để dịch khi chấm)
.venv/bin/python src/check_setup.py
python3 -m unittest discover -s tests -v
```

```bash
export $(grep '^DATABASE_URL=' .env)
.venv/bin/python src/day6_export.py --questions ../Day06/benchmark/questions.json --strategy B --output starter/data/day6
python3 src/build_benchmark.py --chunks starter/data/day6/chunks.json
.venv/bin/python src/run_retrieval.py --split dev --output starter/results/retrieval-dev
.venv/bin/python src/run_agent.py --split dev --top-k 5 --budget 6000 --output starter/results/agent-dev-C1
.venv/bin/python src/run_agent.py --split test --top-k 5 --budget 6000 --output starter/results/agent-test-C1
```

Chi phí đã ghi nhận (Claude + embedding, mọi lần chạy có `summary.json`): khoảng $0,24; chưa gồm phí dịch RouteAPI khi chấm tay và vài lượt chạy thử không lưu summary. Chi tiết tham số, metric và công cụ chấm tay: [src/README.md](src/README.md).

---

## Đề bài

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.
