# Eval results — run 3

- Thời điểm: `2026-07-30T05:08:40.295078+00:00`
- Provider / mode: `gemini` · model: `gemini-3.1-flash-lite`
- Golden set: `D:/HUET-K3-AI-Product-Hackathon/eval/golden-set.jsonl` (22 cases)
- Case chạy bằng **LLM thật**: **22/22** · fallback heuristic: **0/22**
- Quality bar: **≥70% pass** AND **0 case bịa misconception (Q4 khi expect empty)**
- Kết quả: **16/22 = 72.7%** → CHƯA ĐẠT bar

## Lưu ý CP3

> Understanding Estimator gọi **LLM thật** — quyết định trung tâm không hardcode.

## Bảng case

| id | pass | Q1 | Q2 | Q3 | Q4 | score | band exp/act | move | provider |
|---|---|---|---|---|---|---|---|---|---|
| G01 | PASS | Y | Y | Y | Y | 10 | low/low | `validate_understanding` | gemini |
| G02 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G03 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G04 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G05 | FAIL | N | Y | Y | Y | 20 | mid/low | `validate_understanding` | gemini |
| G06 | FAIL | N | Y | Y | Y | 20 | mid/low | `validate_understanding` | gemini |
| G07 | PASS | Y | Y | Y | Y | 80 | mid/high | `validate_understanding` | gemini |
| G08 | FAIL | N | Y | Y | Y | 20 | mid/low | `validate_understanding` | gemini |
| G09 | FAIL | Y | Y | Y | N | 60 | mid/mid | `review_concept` | gemini |
| G10 | FAIL | N | Y | Y | Y | 0 | mid/low | `validate_understanding` | gemini |
| G11 | FAIL | N | Y | Y | Y | 20 | mid/low | `validate_understanding` | gemini |
| G12 | PASS | Y | Y | Y | Y | 0 | low/low | `validate_understanding` | gemini |
| G13 | PASS | Y | Y | Y | Y | 0 | low/low | `validate_understanding` | gemini |
| G14 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G15 | PASS | Y | Y | Y | Y | 0 | low/low | `review_concept` | gemini |
| G16 | PASS | Y | Y | Y | Y | 10 | low/low | `review_concept` | gemini |
| G17 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G18 | PASS | Y | Y | Y | Y | 95 | high/high | `next_topic` | gemini |
| G19 | PASS | Y | Y | Y | Y | 80 | high/high | `validate_understanding` | gemini |
| G20 | PASS | Y | Y | Y | Y | 30 | low/low | `review_concept` | gemini |
| G21 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G22 | PASS | Y | Y | Y | Y | 85 | high/high | `validate_understanding` | gemini |

## Case fail — phân tích

- **G05**: Q1 band (exp=mid act=low score=20). Reason: Học viên yêu cầu giải thích khái niệm tổng quát nhưng chưa đưa ra nội dung cụ thể hoặc tư duy ban đầu.
- **G06**: Q1 band (exp=mid act=low score=20). Reason: Học viên đang đặt câu hỏi cơ bản để phân biệt hai khái niệm và tìm hiểu cấu trúc của LangGraph.
- **G08**: Q1 band (exp=mid act=low score=20). Reason: Học viên chỉ vừa mới bắt đầu yêu cầu giải thích khái niệm cơ bản nên chưa bộc lộ mức độ hiểu bài.
- **G09**: Q4 misconceptions=['Nhầm lẫn giữa giới hạn độ dài phản hồi (max_new_tokens) với khả năng suy luận của mô hình']. Reason: Học viên đã nhận diện được vấn đề kỹ thuật cụ thể khi làm việc với LLM, nhưng chưa cung cấp đủ bối cảnh để đánh giá sâu về kiến thức hệ thống.
- **G10**: Q1 band (exp=mid act=low score=0). Reason: Học viên chỉ yêu cầu giải thích tài liệu mà chưa thể hiện tư duy hay kiến thức nền tảng về vấn đề.
- **G11**: Q1 band (exp=mid act=low score=20). Reason: Học viên chỉ đặt câu hỏi yêu cầu giải thích về hai công nghệ cụ thể mà chưa thể hiện tư duy hay kiến thức nền tảng.

## Phân bố teaching move (output)

- `validate_understanding`: 16
- `review_concept`: 5
- `next_topic`: 1
