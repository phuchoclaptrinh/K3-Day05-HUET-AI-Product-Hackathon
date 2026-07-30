# Eval results — run 1

- Thời điểm: `2026-07-30T04:50:11.231346+00:00`
- Provider / mode: `mock`
- Golden set: `D:/HUET-K3-AI-Product-Hackathon/eval/golden-set.jsonl` (22 cases)
- Quality bar: **≥70% pass** AND **0 case bịa misconception (Q4 khi expect empty)**
- Kết quả: **22/22 = 100.0%** → ĐẠT bar

## Lưu ý CP3

> Run này dùng **heuristic mock** vì chưa có API key. Flow + metric đủ để scaffold; **nộp CP3 chính thức cần re-run với GEMINI_API_KEY hoặc OPENAI_API_KEY** (`LEARNING_ENGINE_MODE=auto`).

## Bảng case

| id | pass | Q1 | Q2 | Q3 | Q4 | score | band exp/act | move | provider |
|---|---|---|---|---|---|---|---|---|---|
| G01 | PASS | Y | Y | Y | Y | 32 | low/low | `validate_understanding` | mock |
| G02 | PASS | Y | Y | Y | Y | 32 | low/low | `validate_understanding` | mock |
| G03 | PASS | Y | Y | Y | Y | 38 | low/low | `validate_understanding` | mock |
| G04 | PASS | Y | Y | Y | Y | 38 | low/low | `validate_understanding` | mock |
| G05 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock |
| G06 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock |
| G07 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock |
| G08 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock |
| G09 | PASS | Y | Y | Y | Y | 42 | mid/mid | `give_example` | mock |
| G10 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock |
| G11 | PASS | Y | Y | Y | Y | 45 | mid/mid | `give_example` | mock |
| G12 | PASS | Y | Y | Y | Y | 15 | low/low | `validate_understanding` | mock |
| G13 | PASS | Y | Y | Y | Y | 15 | low/low | `validate_understanding` | mock |
| G14 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | mock |
| G15 | PASS | Y | Y | Y | Y | 20 | low/low | `validate_understanding` | mock |
| G16 | PASS | Y | Y | Y | Y | 28 | low/low | `review_concept` | mock |
| G17 | PASS | Y | Y | Y | Y | 28 | low/low | `review_concept` | mock |
| G18 | PASS | Y | Y | Y | Y | 78 | high/high | `validate_understanding` | mock |
| G19 | PASS | Y | Y | Y | Y | 78 | high/high | `validate_understanding` | mock |
| G20 | PASS | Y | Y | Y | Y | 28 | low/low | `review_concept` | mock |
| G21 | PASS | Y | Y | Y | Y | 45 | low/mid | `give_example` | mock |
| G22 | PASS | Y | Y | Y | Y | 78 | high/high | `validate_understanding` | mock |

## Case fail — phân tích

Không có case fail.

## Phân bố teaching move (output)

- `validate_understanding`: 11
- `give_example`: 8
- `review_concept`: 3
