# Learning Engine — AI Tutor (Hướng A · VLearn)

Prototype **Learning Intelligence Layer** trên AI Tutor: ước lượng mức hiểu → phát hiện misconception → chọn teaching move → sinh follow-up.

## Mức prototype

| Phần | Mức | Ghi chú |
|---|---|---|
| Understanding Estimator + Misconception | **Working** khi có API key | 1 LLM call JSON (Gemini ưu tiên, OpenAI fallback) |
| Teaching Strategy Selector | **Working** | Rule-based |
| Follow-up Generator | **Working** | Template có điều kiện |
| Tutor response | **Working** / Mock | LLM nếu có key; template nếu mock |
| Dashboard KPI | **Working** tối thiểu | Trong Streamlit |

Không có API key → chế độ `mock` (heuristic) để bấm flow + chạy eval scaffold; **CP3 chính thức cần ≥1 LLM call thật** — set key rồi chạy lại.

## Setup

```bash
cd codebase
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # điền GEMINI_API_KEY hoặc OPENAI_API_KEY
```

## Chạy UI (CP2/CP3)

```bash
cd codebase
streamlit run app.py
```

## Chạy eval lượt đo (CP3)

```bash
# Từ root repo — dùng model nhẹ + nghỉ 5s/case để tránh 429 free tier
python eval/run_eval.py --run 5 --model gemini-3.1-flash-lite --sleep 5
```

Luật chấm và lịch sử các lượt đo: [`../eval/README.md`](../eval/README.md).

## Khi key không được nhận

| Triệu chứng | Nguyên nhân | Cách xử lý |
|---|---|---|
| UI vẫn hiện cảnh báo mock sau khi điền key | Streamlit đã start **trước** khi `.env` có key; `.env` chỉ được đọc lúc import module | Ctrl+C rồi `streamlit run app.py` lại |
| Đúng key nhưng vẫn ra `mock` | Biến môi trường `LEARNING_ENGINE_MODE=mock` còn sót trong shell | Đã xử lý: `codebase/.env` được load với `override=True` nên thắng biến shell |
| `429 RESOURCE_EXHAUSTED` | Hết quota free tier | Tăng `--sleep`, hoặc đổi `GEMINI_MODEL` sang bản `flash-lite` |
| `404 model not found` | Tên model không tồn tại với key đang dùng | Liệt kê model khả dụng bằng `client.models.list()` của `google-genai` |

Engine tự fallback về heuristic khi LLM lỗi để demo không bị đứng; report eval **đếm riêng** số case fallback nên không che số liệu.

## Cấu trúc

```
codebase/
  app.py                 # Streamlit: chat + signals + dashboard
  learning_engine/
    context.py
    llm_client.py
    estimator.py         # quyết định trung tâm (LLM)
    strategy.py
    followup.py
    response.py
    pipeline.py
```
