# Reflection cá nhân — Nguyễn Ngọc Dương · 2A202601717

**Hackathon:** HUET K3 — AI Product Hackathon · Batch 03  
**Nhóm:** Learning Engine  
**Hướng:** A — VLearn (Tối ưu AI Tutor hiện có)  
**Ngày:** 2026-07-31

---

## 1. Vai trò & phần tôi phụ trách

Trong nhóm tôi chịu trách nhiệm chính cho ba phần:

| Phần | Mô tả ngắn |
|---|---|
| **Strategy Selector** (`codebase/learning_engine/strategy.py`) | Rule-based engine chọn teaching move dựa trên score, confidence, misconceptions |
| **Follow-up Generator** (`codebase/learning_engine/followup.py`) | Sinh câu hỏi MCQ kiểm tra hiểu bài — LLM call (Gemini) khi có key, template khi mock/quota hết |
| **Streamlit UI** (`codebase/app.py`) | Giao diện chat + panel signals (score, confidence, teaching move) + KPI session |

---

## 2. Những gì tôi đã làm cụ thể

### Strategy Selector (`strategy.py`)

Module rule-based thuần, không gọi LLM:
- Nhận đầu vào: `understanding_score` (0–100), `confidence` (low/medium/high), `misconceptions` (list).
- Priority rule: **misconception → low confidence → score band**.
- Trả về `StrategyResult` gồm `teaching_strategy` + 5 flag boolean (`need_review`, `need_example`, `need_hint`, `need_check`, `need_next`).
- Ánh xạ 5 moves: `review_concept`, `give_example`, `validate_understanding`, `give_hint`, `next_topic`.

Lý do thiết kế rule-based: cost-of-error khi AI chọn sai move là học viên học lệch kiến thức ngay → giữ logic xác định, dễ debug và eval được (Q2 trong golden set).

### Follow-up Generator (`followup.py`)

- Prompt hệ thống yêu cầu LLM sinh **đúng 1 câu trắc nghiệm** (4 đáp án A/B/C/D) theo teaching strategy, misconception và lesson excerpt hiện tại.
- Có `_normalize_mcq()` để validate và chuẩn hóa JSON trả về từ LLM trước khi dùng.
- Fallback về `_template_check_question()` khi LLM lỗi / quota hết / mock mode — có template chuyên biệt cho các khái niệm hay gặp (MVP, Stack/Queue v.v.).
- Export hàm `grade_check_answer` để UI chấm đáp án học viên chọn ngay trong chat.

### Streamlit UI (`app.py`)

- Layout: cột chat chính + sidebar signals (understanding score, confidence, reasoning, misconceptions, teaching move).
- Mỗi turn hiển thị: câu trả lời tutor → ví dụ minh họa (nếu có) → MCQ kiểm tra (nếu có) → nút "Bỏ qua gợi ý" (G8).
- Panel KPI session: tổng lượt, phân bố teaching moves, % asked_check_question.
- Tích hợp Flow Lab (trace cache → golden fixture → API) để demo không phụ thuộc quota.
- Xử lý scope guard UI: khi in_scope=False, không render example/MCQ, chỉ hiện thông báo từ chối.

---

## 3. AI đã hỗ trợ tôi như thế nào

Tôi dùng AI (Gemini + Claude) trong quá trình build theo các cách:

| Mục đích | Cách dùng | Đánh giá |
|---|---|---|
| Soạn thảo SYSTEM_PROMPT cho Follow-up Generator | Nhờ AI gợi ý cấu trúc JSON schema, quy tắc "câu hỏi đóng" | Tiết kiệm thời gian viết prompt iteration đầu tiên; vẫn phải sửa rule cấm câu hỏi mở |
| Debug normalize MCQ | Hỏi AI giải thích cách xử lý khi LLM trả JSON không đúng schema | Hữu ích để thêm guard cho `correct_option not in options` |
| Thiết kế layout Streamlit | Hỏi cách tổ chức `st.columns`, session_state | Gợi ý đúng hướng; phần custom CSS và UX flow vẫn tự quyết |
| Viết template fallback MCQ | Nhờ AI gợi 2–3 template câu hỏi, sau đó tôi điều chỉnh cho đúng tone VLearn | Nhanh hơn viết từ đầu; cần check distractor hợp lý |

**Điều quan trọng:** Mọi logic chính (priority rule của strategy, schema MCQ, cách render UI) tôi tự quyết định và có thể giải thích lại tại CP5/CP6 vì tôi hiểu từng dòng code.

---

## 4. Một bài học từ case fail của nhóm

**Case fail: G07** (run 5, `eval/results-run5.md`)

> Học viên dán nguyên văn đoạn slide → Estimator cho `score=90` (high) → move `next_topic` → bỏ qua MCQ kiểm tra.  
> Kỳ vọng: score phải low (vì chỉ paste, chưa tự diễn đạt).

**Vì sao xảy ra?**  
Context truyền vào Estimator không có slide excerpt gốc để so sánh. Model chỉ nhìn *nội dung* câu trả lời — nghe "đúng" về mặt ngữ nghĩa → cho điểm cao.

**Bài học của tôi (góc strategy/followup):**  
Khi `teaching_strategy=next_topic` và `asked_check_question=False`, pipeline bỏ qua MCQ — đây đúng theo rule, nhưng lộ điểm yếu: **rule tin vào score tuyệt đối mà không có context về nguồn gốc câu trả lời (tự diễn đạt vs. copy-paste)**.

Hướng sửa đã thảo luận với nhóm:  
1. Estimator cần nhận thêm `slide_excerpt` → so sánh overlap với câu của HV.  
2. Strategy thêm rule: nếu `overlap_ratio > threshold` → hạ move về `validate_understanding` thay vì `next_topic`.  
3. Follow-up Generator: khi move là `validate_understanding`, prompt nhấn mạnh "hãy dùng ví dụ của chính mình".

**Bài học chung:** Rule-based strategy chạy nhanh và kiểm soát được, nhưng chỉ tốt bằng chất lượng signal đầu vào. Cần đầu tư vào việc làm giàu context trước khi gọi Estimator, không chỉ xử lý output sau.

---

## 5. Nhìn lại quy trình nhóm

**Điều làm tốt:**
- Spec-first: viết spec trước khi code → giúp tôi biết chính xác interface cần implement (`StrategyResult`, `CheckQuestion`) từ đầu.
- Eval scaffold sớm: có golden set từ CP3 → tôi test được strategy rule trước khi LLM ổn định.
- Phân chia rõ: mỗi người 1 module → ít conflict; `pipeline.py` đóng vai "keo dán" assembly.

**Điều cần cải thiện:**
- Template fallback MCQ còn generic — nếu có thêm thời gian, nên xây template theo từng chủ đề khoá học.
- UI signals panel cần tooltip giải thích "score là gì" cho người dùng lần đầu — hiện tại chỉ hiện con số.

---

> *Tôi xác nhận: phần strategy, follow-up và UI trong repo là do tôi trực tiếp viết và có thể giải thích tại CP5/CP6.*
