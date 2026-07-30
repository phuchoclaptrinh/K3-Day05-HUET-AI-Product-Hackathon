# Eval results — run 2

- Thời điểm: `2026-07-30T05:03:41.154195+00:00`
- Provider / mode: `gemini`
- Golden set: `D:/HUET-K3-AI-Product-Hackathon/eval/golden-set.jsonl` (22 cases)
- Quality bar: **≥70% pass** AND **0 case bịa misconception (Q4 khi expect empty)**
- Kết quả: **21/22 = 95.5%** → ĐẠT bar

## Lưu ý CP3

> Understanding Estimator gọi **LLM thật** — quyết định trung tâm không hardcode.

## Bảng case

| id | pass | Q1 | Q2 | Q3 | Q4 | score | band exp/act | move | provider |
|---|---|---|---|---|---|---|---|---|---|
| G01 | PASS | Y | Y | Y | Y | 30 | low/low | `validate_understanding` | gemini |
| G02 | PASS | Y | Y | Y | Y | 30 | low/low | `validate_understanding` | gemini |
| G03 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | gemini |
| G04 | PASS | Y | Y | Y | Y | 38 | low/low | `validate_understanding` | mock_fallback |
| G05 | FAIL | N | Y | Y | Y | 20 | mid/low | `validate_understanding` | gemini |
| G06 | PASS | Y | Y | Y | Y | 30 | mid/low | `validate_understanding` | gemini |
| G07 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock_fallback |
| G08 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock_fallback |
| G09 | PASS | Y | Y | Y | Y | 42 | mid/mid | `give_example` | mock_fallback |
| G10 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock_fallback |
| G11 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock_fallback |
| G12 | PASS | Y | Y | Y | Y | 15 | low/low | `validate_understanding` | mock_fallback |
| G13 | PASS | Y | Y | Y | Y | 15 | low/low | `validate_understanding` | mock_fallback |
| G14 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | mock_fallback |
| G15 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | mock_fallback |
| G16 | PASS | Y | Y | Y | Y | 28 | low/low | `review_concept` | mock_fallback |
| G17 | PASS | Y | Y | Y | Y | 20 | low/low | `review_concept` | gemini |
| G18 | PASS | Y | Y | Y | Y | 78 | high/high | `validate_understanding` | mock_fallback |
| G19 | PASS | Y | Y | Y | Y | 78 | high/high | `validate_understanding` | mock_fallback |
| G20 | PASS | Y | Y | Y | Y | 28 | low/low | `review_concept` | mock_fallback |
| G21 | PASS | Y | Y | Y | Y | 45 | low/mid | `give_example` | mock_fallback |
| G22 | PASS | Y | Y | Y | Y | 78 | high/high | `validate_understanding` | mock_fallback |

## Case fail — phân tích

- **G05**: Q1 band (exp=mid act=low score=20). Reason: Học viên mới chỉ yêu cầu giải thích về '4 chiến lược' và chưa bộc lộ tư duy hay mức độ hiểu biết cá nhân.

## Phân bố teaching move (output)

- `validate_understanding`: 13
- `give_example`: 6
- `review_concept`: 3
