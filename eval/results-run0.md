# Eval results — run 0

- Thời điểm: `2026-07-31T03:08:59.732395+00:00`
- Provider / mode: `gemini` · model: `gemini-3.1-flash-lite`
- Golden set: `D:/HUET-K3-AI-Product-Hackathon/eval/golden-set.jsonl` (22 cases)
- Case chạy bằng **LLM thật**: **14/22** · fallback heuristic: **8/22**
- Quality bar: **≥70% pass** AND **0 case bịa misconception (Q4 khi expect empty)**
- Kết quả: **9/22 = 40.9%** → CHƯA ĐẠT bar

## Lưu ý CP3

> Understanding Estimator gọi **LLM thật** — quyết định trung tâm không hardcode.

> **8 case** bị rơi về heuristic fallback do lỗi LLM (chủ yếu `429 RESOURCE_EXHAUSTED` — quota free tier). Ghi nhận trung thực; tăng `--sleep` hoặc đổi `GEMINI_MODEL` sang bản flash-lite để chạy lại.

## Bảng case

| id | pass | Q1 | Q2 | Q3 | Q4 | score | band exp/act | move | provider |
|---|---|---|---|---|---|---|---|---|---|
| G01 | PASS | Y | Y | Y | Y | 25 | low/low | `review_concept` | gemini |
| G02 | PASS | Y | Y | Y | Y | 30 | low/low | `review_concept` | gemini |
| G03 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G04 | PASS | Y | Y | Y | Y | 25 | low/low | `validate_understanding` | gemini |
| G05 | FAIL | Y | N | N | Y | 0 | low/low | `out_of_scope` | skipped |
| G06 | PASS | Y | Y | Y | Y | 30 | low/low | `validate_understanding` | gemini |
| G07 | PASS | Y | Y | Y | Y | 35 | low/low | `validate_understanding` | gemini |
| G08 | PASS | Y | Y | Y | Y | 25 | low/low | `validate_understanding` | gemini |
| G09 | FAIL | N | Y | Y | Y | 35 | mid/low | `validate_understanding` | gemini |
| G10 | PASS | Y | Y | Y | Y | 25 | low/low | `validate_understanding` | gemini |
| G11 | PASS | Y | Y | Y | Y | 35 | low/low | `validate_understanding` | gemini |
| G12 | FAIL | Y | N | N | Y | 0 | low/low | `out_of_scope` | skipped |
| G13 | FAIL | Y | N | N | Y | 0 | low/low | `out_of_scope` | skipped |
| G14 | FAIL | Y | N | N | Y | 0 | low/low | `out_of_scope` | skipped |
| G15 | FAIL | Y | N | N | Y | 0 | low/low | `out_of_scope` | skipped |
| G16 | FAIL | Y | N | N | N | 0 | low/low | `out_of_scope` | skipped |
| G17 | FAIL | Y | Y | Y | N | 25 | low/low | `validate_understanding` | gemini |
| G18 | FAIL | N | Y | Y | Y | 35 | high/low | `validate_understanding` | gemini |
| G19 | FAIL | N | Y | Y | Y | 35 | high/low | `validate_understanding` | gemini |
| G20 | FAIL | Y | N | N | N | 0 | low/low | `out_of_scope` | skipped |
| G21 | FAIL | Y | N | N | Y | 0 | low/low | `out_of_scope` | skipped |
| G22 | FAIL | N | Y | Y | N | 35 | high/low | `review_concept` | gemini |

## Case fail — phân tích

- **G05**: Q2 move, Q3 follow-up. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G09**: Q1 band (exp=mid act=low score=35). Reason: Tin nhắn trùng cao với excerpt slide — chưa phải bằng chứng tự hiểu. Học viên đang nêu ra một vấn đề kỹ thuật thực tế gặp phải khi dùng LLM thay vì diễn đạt lại kiến thức từ nội dung bài học. Câu hỏi mang tính chất tìm kiếm sự hỗ trợ lỗi kỹ thuật hơn là thể hiện sự hiểu bài.
- **G12**: Q2 move, Q3 follow-up. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G13**: Q2 move, Q3 follow-up. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G14**: Q2 move, Q3 follow-up. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G15**: Q2 move, Q3 follow-up. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G16**: Q2 move, Q3 follow-up, Q4 misconceptions=[]. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G17**: Q4 misconceptions=[]. Reason: Tin nhắn trùng cao với excerpt slide — chưa phải bằng chứng tự hiểu. Học viên đưa ra nhận định sai về độ phức tạp của thuật toán và nội dung này không thuộc phạm vi bài học (Transformer/LLM limitations).
- **G18**: Q1 band (exp=high act=low score=35). Reason: Học viên có nỗ lực tổng hợp kiến thức từ bài giảng, nhưng cách diễn đạt bị trùng lặp với từ ngữ trong tài liệu, dẫn đến điểm evidence thấp do nghi vấn sao chép.
- **G19**: Q1 band (exp=high act=low score=35). Reason: Tin nhắn trùng cao với excerpt slide — chưa phải bằng chứng tự hiểu. Học viên đã cố gắng tự diễn đạt khái niệm context window bằng cách so sánh với 'bàn làm việc có giới hạn', thể hiện khả năng nắm bắt ý chính từ slide.
- **G20**: Q2 move, Q3 follow-up, Q4 misconceptions=[]. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G21**: Q2 move, Q3 follow-up. Reason: Ngoài phạm vi khoá — không ước lượng hiểu bài.
- **G22**: Q1 band (exp=high act=low score=35), Q4 misconceptions=['Cho rằng có 4 chiến lược tối ưu context cụ thể là Write/Select/Compress/Isolate trong nội dung buổi học.']. Reason: Học viên liệt kê các chiến lược (Write/Select/Compress/Isolate) không xuất hiện trong nội dung excerpt được cung cấp về giới hạn LLM. Câu trả lời mang tính chất suy diễn ngoài phạm vi bài học (hallucinated context).

## Phân bố teaching move (output)

- `validate_understanding`: 10
- `out_of_scope`: 8
- `review_concept`: 4
