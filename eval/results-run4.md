# Eval results — run 4

- Thời điểm: `2026-07-30T05:14:15.447010+00:00`
- Provider / mode: `gemini` · model: `gemini-3.1-flash-lite`
- Golden set: `D:/HUET-K3-AI-Product-Hackathon/eval/golden-set.jsonl` (22 cases)
- Case chạy bằng **LLM thật**: **22/22** · fallback heuristic: **0/22**
- Quality bar: **≥70% pass** AND **0 case bịa misconception (Q4 khi expect empty)**
- Kết quả: **18/22 = 81.8%** → CHƯA ĐẠT bar

## Lưu ý CP3

> Understanding Estimator gọi **LLM thật** — quyết định trung tâm không hardcode.

## Bảng case

| id | pass | Q1 | Q2 | Q3 | Q4 | score | band exp/act | move | provider |
|---|---|---|---|---|---|---|---|---|---|
| G01 | PASS | Y | Y | Y | Y | 10 | low/low | `validate_understanding` | gemini |
| G02 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G03 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G04 | PASS | Y | Y | Y | Y | 10 | low/low | `validate_understanding` | gemini |
| G05 | PASS | Y | Y | Y | Y | 10 | low/low | `validate_understanding` | gemini |
| G06 | FAIL | Y | Y | Y | N | 30 | low/low | `review_concept` | gemini |
| G07 | FAIL | N | Y | Y | Y | 80 | low/high | `validate_understanding` | gemini |
| G08 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G09 | FAIL | Y | Y | Y | N | 40 | mid/mid | `review_concept` | gemini |
| G10 | PASS | Y | Y | Y | Y | 10 | low/low | `validate_understanding` | gemini |
| G11 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G12 | PASS | Y | Y | Y | Y | 0 | low/low | `validate_understanding` | gemini |
| G13 | PASS | Y | Y | Y | Y | 0 | low/low | `validate_understanding` | gemini |
| G14 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G15 | PASS | Y | Y | Y | Y | 0 | low/low | `review_concept` | gemini |
| G16 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G17 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G18 | PASS | Y | Y | Y | Y | 95 | high/high | `next_topic` | gemini |
| G19 | FAIL | N | Y | Y | N | 70 | high/mid | `review_concept` | gemini |
| G20 | PASS | Y | Y | Y | Y | 30 | low/low | `review_concept` | gemini |
| G21 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G22 | PASS | Y | Y | Y | Y | 85 | high/high | `validate_understanding` | gemini |

## Case fail — phân tích

- **G06**: Q4 misconceptions=['Đánh đồng React (thư viện UI) và LangGraph (framework cho đại lý AI) trong cùng một hệ quy chiếu kỹ thuật']. Reason: Học viên đang đặt câu hỏi so sánh cơ bản và tìm hiểu phân loại, cho thấy chưa có kiến thức nền tảng về công nghệ này.
- **G07**: Q1 band (exp=low act=high score=80). Reason: Học viên đã nắm bắt được bản chất cốt lõi của LLM là mô hình dự đoán token tiếp theo dựa trên bối cảnh.
- **G09**: Q4 misconceptions=['Nhầm lẫn việc model tự dừng với các thiết lập giới hạn token (max_tokens) hoặc điều kiện dừng (stop sequences).']. Reason: Học viên nhận diện được vấn đề kỹ thuật với model nhưng chưa hiểu rõ về cơ chế giới hạn token hoặc stop sequence trong LLM.
- **G19**: Q1 band (exp=high act=mid score=70), Q4 misconceptions=['Khả năng coi context là một không gian vật lý tĩnh (bàn làm việc) thay vì là một chuỗi token có giới hạn dung lượng xử lý']. Reason: Học viên đã nắm được khái niệm cơ bản về ngữ cảnh (context) trong mô hình ngôn ngữ và đang cố gắng dùng phép ẩn dụ để làm rõ tư duy.

## Phân bố teaching move (output)

- `validate_understanding`: 14
- `review_concept`: 7
- `next_topic`: 1
