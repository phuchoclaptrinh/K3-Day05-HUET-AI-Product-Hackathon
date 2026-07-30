# Eval results — run 5

- Thời điểm: `2026-07-30T05:17:49.194490+00:00`
- Provider / mode: `gemini` · model: `gemini-3.1-flash-lite`
- Golden set: `D:/HUET-K3-AI-Product-Hackathon/eval/golden-set.jsonl` (22 cases)
- Case chạy bằng **LLM thật**: **22/22** · fallback heuristic: **0/22**
- Quality bar: **≥70% pass** AND **0 case bịa misconception (Q4 khi expect empty)**
- Kết quả: **21/22 = 95.5%** → ĐẠT bar

## Lưu ý CP3

> Understanding Estimator gọi **LLM thật** — quyết định trung tâm không hardcode.

## Bảng case

| id | pass | Q1 | Q2 | Q3 | Q4 | score | band exp/act | move | provider |
|---|---|---|---|---|---|---|---|---|---|
| G01 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G02 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G03 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G04 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G05 | PASS | Y | Y | Y | Y | 10 | low/low | `review_concept` | gemini |
| G06 | PASS | Y | Y | Y | Y | 30 | low/low | `review_concept` | gemini |
| G07 | FAIL | N | Y | Y | Y | 90 | low/high | `next_topic` | gemini |
| G08 | PASS | Y | Y | Y | Y | 10 | low/low | `review_concept` | gemini |
| G09 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | gemini |
| G10 | PASS | Y | Y | Y | Y | 10 | low/low | `review_concept` | gemini |
| G11 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G12 | PASS | Y | Y | Y | Y | 0 | low/low | `review_concept` | gemini |
| G13 | PASS | Y | Y | Y | Y | 0 | low/low | `review_concept` | gemini |
| G14 | PASS | Y | Y | Y | Y | 0 | low/low | `review_concept` | gemini |
| G15 | PASS | Y | Y | Y | Y | 0 | low/low | `review_concept` | gemini |
| G16 | PASS | Y | Y | Y | Y | 10 | low/low | `review_concept` | gemini |
| G17 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G18 | PASS | Y | Y | Y | Y | 95 | high/high | `next_topic` | gemini |
| G19 | PASS | Y | Y | Y | Y | 85 | high/high | `validate_understanding` | gemini |
| G20 | PASS | Y | Y | Y | Y | 30 | low/low | `review_concept` | gemini |
| G21 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G22 | PASS | Y | Y | Y | Y | 90 | high/high | `next_topic` | gemini |

## Case fail — phân tích

- **G07**: Q1 band (exp=low act=high score=90). Reason: Học viên đã tự diễn đạt lại khái niệm cốt lõi của LLM một cách ngắn gọn, chính xác bằng lời văn của bản thân.

## Phân bố teaching move (output)

- `review_concept`: 17
- `next_topic`: 3
- `give_example`: 1
- `validate_understanding`: 1
