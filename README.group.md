# AI Tutor Learning Engine — repo nhóm (Hackathon Batch 03)

**Hướng:** A — VLearn · tối ưu AI Tutor  
**Lát cắt:** Học viên đang học trong lớp · muốn biết mình đã hiểu khái niệm vừa hỏi chưa · hệ thống ước lượng mức hiểu + chọn teaching move · học viên nhận câu hỏi kiểm tra / bước học tiếp.

> Pipeline chi tiết: [`docs/00-pipeline-trien-khai.md`](docs/00-pipeline-trien-khai.md)

## Thành viên & phân công *(điền tên tại CP1)*

| Mã HV | Tên | Phụ trách |
|---|---|---|
| | | Spec (`spec.md`) |
| | | Evidence / mining |
| | | Prompt + Estimator / Misconception |
| | | Strategy + Follow-up + `codebase/` |
| | | Eval golden set + results |
| | | Demo slides |

## Cấu trúc

```
docs/00-pipeline-trien-khai.md
codebase/          ← Streamlit Learning Engine (xem codebase/README.md)
eval/              ← golden-set + results-run1 + evidence
validation/        ← (CP5)
spec.md            ← chốt 23:59 N1
```

## Chạy nhanh (đến CP3)

```bash
cd codebase
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Điền GEMINI_API_KEY hoặc OPENAI_API_KEY để có LLM thật

streamlit run app.py
```

Đo lượt 1:

```bash
python eval/run_eval.py --run 1
```

## Bảo mật data

- Không commit `data/**/*.csv` / API key.
- Golden set chỉ dùng mã `Txxxx`/`Cxxxx` + trích ngắn.
