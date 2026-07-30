# AI SPEC — Learning Intelligence Layer cho AI Tutor · Nhóm Learning Engine · Zone _
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở  
Loại: [x] Tối ưu tính năng có sẵn  [ ] Tính năng mới  

**Thành viên:** Ngô Hùng Phúc (2A202601069) · Nguyễn Văn Linh (2A202601971) · Nguyễn Duy Hoàng (2A202601147) · Nguyễn Ngọc Dương (2A202601717) · Lê Văn Long (2A20261711)

Canvas CP1: [`docs/canvas-cp1.md`](docs/canvas-cp1.md) · Pipeline: [`docs/00-pipeline-trien-khai.md`](docs/00-pipeline-trien-khai.md)

---

## §1. User & Job

- **Job executor + workflow** (đính kèm worksheet JTBD / ảnh sơ đồ):  
  Học viên đang học **in-class** trên VLearn → bôi đen đoạn slide / hỏi tutor về khái niệm → nhận câu trả lời → (hiện tại) conversation thường kết thúc mà không được kiểm tra hiểu bài.  
  Worksheet JTBD tham chiếu: [`tham-khao/worksheet-jtbd-day-du.md`](tham-khao/worksheet-jtbd-day-du.md).

- **Core JTBD** (không tên sản phẩm/AI trong câu):  
  *Khi vừa hỏi về một khái niệm trong buổi học, tôi muốn biết mình đã hiểu đến đâu và cần làm gì tiếp, để không chỉ nhận câu trả lời rồi bỏ qua mà vẫn chưa nắm bài.*

- **Problem statement** (KHÔNG chữ AI):  
  Học viên nhận được câu trả lời từ tutor nhưng không biết mình đã hiểu thật chưa, không được kiểm tra lại, không được phát hiện chỗ hiểu sai, và không có bước học tiếp — hậu quả: tưởng đã hiểu, mang lỗ hổng sang phần sau / quiz.

- **Evidence** (chuẩn **B** — mining; khuyến nghị bổ sung A trước CP5):  
  - Số liệu mining (`scripts/mine_evidence.py` → [`eval/evidence-quotes.md`](eval/evidence-quotes.md)):  
    - 2.522 messages · 1.261 turns tutor · `asked_check_question=True` chỉ **3/2522**  
    - `misconceptions` / `follow_ups` = **100% rỗng** (1261/1261)  
    - `move_used=review_concept` ≈ **85,2%** (1074/1261); `validate_understanding` chỉ **1** turn  
  - ≥5 quote/ví dụ nguyên văn + nguồn: T0649, T0990, T1026, T0930, T1001 (trích trong `eval/evidence-quotes.md`, mã hội thoại từ chatlog VLearn — không commit CSV gốc).

---

## §2. Impact & quyết định chọn

- **Bảng impact ≥3 ứng viên:**

| Ứng viên | Bao nhiêu người gặp | Tần suất | Mỗi lần tốn gì | Build nổi? | Quyết định |
|---|---|---|---|---|---|
| A. Learning Intelligence Layer (understanding + misconception + strategy + follow-up) | ~mọi HV dùng tutor in-class (369 user / tuần data; gần 100% turn không check-question) | Mỗi turn hỏi khái niệm | Tưởng hiểu → lỗ hổng kiến thức; mất cơ hội consolidate | Có | **CHỌN** |
| B. Chỉ cải thiện citation / grounding trang | ~46% turn `citations=[]` | Mỗi câu trả lời không cite | Mất niềm tin / khó đối chiếu tài liệu | Có | LOẠI |
| C. Chỉ thêm check-question cuối buổi / cuối hội thoại | HV kết thúc session | 1 lần / session | Adaptive muộn; data cho thấy gần như 0 check cả conversation | Có | LOẠI |

- **Ứng viên ĐÃ LOẠI + vì sao:**  
  - B: pain citation thật nhưng không giải “đã hiểu chưa?”.  
  - C: hẹp hơn A; không lấp được misconception/follow-up đang trống trong data.

- **Ứng viên CHỌN + vì sao (bằng số):**  
  A — vì 85% turn chỉ `review_concept` + 0% misconceptions/follow_ups + ~0% check-question → tutor đang tối ưu trả lời, chưa tối ưu dạy. A tạo KPI đo được và đụng đúng field dataset đang trống/`False`.

---

## §3. Giải pháp tương tự đã nghiên cứu

- **ChatGPT Study Mode / Custom GPT “tutor”:**  
  - Flow: hỏi → giải thích → đôi khi hỏi lại.  
  - Đáng học: chủ động hỏi để kiểm tra hiểu.  
  - Đáng né: không có score/misconception có cấu trúc; khó đo KPI.  
  - Mình khác: tách **Understanding Estimator** (score + reason + confidence) và **rule strategy** có thể giải thích / eval được.

- **Khanmigo:**  
  - Flow: gợi ý từng bước, hạn chế đưa đáp án thẳng.  
  - Đáng học: không làm hộ; scaffold bằng câu hỏi.  
  - Đáng né: khó nhìn “mức hiểu %” và phân bố teaching move.  
  - Mình khác: surface score + move + misconception trên UI; map field VLearn (`misconceptions`, `follow_ups`, `asked_check_question`).

- **Duolingo / Quizlet AI (tham khảo nhẹ):**  
  - Đáng học: adaptive theo tín hiệu đúng/sai.  
  - Đáng né: quiz-first, không phải tutor in-class bám slide.  
  - Mình khác: bám hội thoại in-class VLearn, không thay quiz chính thức.

---

## §4. Thiết kế

- **Lát cắt MỘT CÂU** (1 user · 1 việc · 1 quyết định AI · 1 kết quả):  
  *Học viên đang học trong lớp · muốn biết mình đã hiểu khái niệm vừa hỏi chưa · hệ thống ước lượng mức hiểu + chọn teaching move · học viên nhận câu hỏi kiểm tra / bước học tiếp phù hợp.*

- **Non-goals (≥3):**  
  1. Không rebuild toàn bộ AI Tutor / RAG / citation engine.  
  2. Không làm dashboard giảng viên full-class analytics.  
  3. Không fine-tune / train model riêng.  
  4. Không thay thế giảng viên / chấm điểm chính thức.  
  5. Không xử lý logistics Discord / deadline.

- **Mức prototype nhắm tới:** [ ] Sketch  [ ] Mock  [x] Working  
  - **Thật:** Understanding Estimator + Misconception (Gemini JSON), Follow-up Generator (Gemini), Tutor Response (Gemini), Strategy Selector (rules), **Scope Guard** (local, chặn ngoài phạm vi trước API), **Example Illustrator** (ví dụ minh họa), UI Streamlit + Flow Lab + KPI session.  
  - **Mock / fallback:** heuristic mock khi hết quota/lỗi API; Flow Lab HIT golden-set dùng fixture local (không gọi API); eval follow-up dùng template để tiết kiệm quota.

- **Automation:** [ ] augment  [x] conditional  [ ] automate  
  - **Lý do cost-of-error:** sai kiến thức / bịa misconception → học viên học lệch ngay (đắt) → không automate full; Augment thuần thì không lấp được `asked_check_question`. Conditional: tự chọn move + follow-up khi đủ tín hiệu; `confidence=low` → hỏi làm rõ, không gán misconception.

- **§4b. Nguyên tắc đã áp dụng (≥4 — HAX/PAIR):**

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| **G1** — Làm rõ hệ thống làm được gì | Hero + expander “VLearn Tutor có thể hỗ trợ gì?”: ước lượng hiểu + bước học tiếp — không chấm điểm chính thức |
| **G2** — Làm rõ làm tốt đến đâu | Panel hiện `understanding_score`, `confidence`, `understanding_reason` cạnh mỗi turn |
| **G8** — Gạt bỏ dễ dàng | Nút “Bỏ qua gợi ý”; chat vẫn nhận câu hỏi tự do |
| **G10** — Thu hẹp khi nghi | Prompt Estimator: `confidence=low` + cấm bịa misconception khi chỉ hỏi mở / tóm tắt |
| **G11** — Giải thích vì sao | `understanding_reason` hiển thị trong panel “Vì sao hệ thống đánh giá như vậy?” |

---

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

### 4 lớp cụ thể hoá

| Lớp | Cụ thể lát cắt này |
|---|---|
| ① Nguồn sự thật | Không có ground truth understanding → chỉ dựa hội thoại; cấm suy diễn misconception ngoài text; không bịa số trang |
| ② Mơ hồ / thiếu thông tin | Xin tóm tắt / greeting / tin ngắn → `confidence=low`, hỏi làm rõ, `misconceptions=[]` |
| ③ Ngoài phạm vi / thẩm quyền | Làm hộ bài, đáp án quiz, giải mã base64, chấm điểm chính thức → từ chối + vẫn hữu ích trong phạm vi học |
| ④ Đặc thù domain | Phát biểu sai kiến thức → phải phát hiện misconception; bịa misconception / sai move → HV học lệch |

### ≥8 kịch bản

| # | Tình huống | Lớp | Hành vi mong muốn | Nguyên tắc |
|---|---|---|---|---|
| 1 | “tóm tắt trang 37” — chưa lộ tư duy | ② | Score low, confidence=low, misconceptions=[], hỏi kiểm tra | G10 |
| 2 | HV diễn đạt lại đúng khái niệm bằng lời mình | — | Score high, move check/next, follow-up ngắn | G2 |
| 3 | Nhầm Stack/Queue trong câu khẳng định | ④ | Có misconception cụ thể, review_concept, follow-up phân biệt | G11 |
| 4 | Hỏi lại cùng khái niệm nhiều lần | ① | Score thấp, reason nêu hỏi lặp, review + check | G11 |
| 5 | Input ngắn (“hi”, “asds”) | ② | Không bịa misconception; hỏi lại 1 câu / Scope Guard | G10 |
| 6 | “làm hộ bài / cho đáp án quiz” | ③ | **Scope Guard** từ chối local, **không gọi API** ước lượng/dạy | G1 |
| 7 | Giải mã base64 / ngoài học thuật | ③ | Scope Guard từ chối ngoài phạm vi (không gọi API) | G1 |
| 8 | Estimator lệch band so với judge người (vd. G07) | ① | Ghi fail trong eval; UI vẫn cho bỏ qua follow-up | G8 |
| 9 | Không có excerpt slide | ① | Ước lượng theo wording; không bịa trang; có thể dùng topic_hint | G2 |
| 10 | Score cao sau 1 câu may rủi | ④ | Follow-up nhẹ xác nhận trước khi next_topic | G10 |

---

## §6. Bốn đường đi của trải nghiệm

- **Happy path:** HV hỏi khái niệm trong phạm vi → ví dụ minh họa + score + strategy + MCQ kiểm tra.  
- **Low-confidence (②):** Xin tóm tắt / mơ hồ → confidence=low, không gán misconception, hỏi làm rõ (validate_understanding / check).  
- **Failure / không căn cứ (①):** Thiếu tín hiệu hoặc lệch band → thu hẹp: không bịa misconception; log fail trong eval; user bỏ qua follow-up được.  
- **Correction:** HV trả lời follow-up ở turn sau → Estimator cập nhật score/move theo tin mới.  
- **Ngoài phạm vi (③):** Scope Guard từ chối local (**skip API**) + gợi ý hỏi lại trong phạm vi khoá.  
- **Đặc thù domain (④):** Phát hiện misconception cụ thể → review_concept + follow-up sửa chỗ sai (không để trống follow-up).

Prototype: chat chính + panel signals + Flow Lab (trace cache → golden → API).

---

## §7. Kiểm thử

- **Chiều chất lượng + định nghĩa kiểm chứng được** (chi tiết [`eval/README.md`](eval/README.md)):  
  - **Q1 Band:** score thuộc đúng band kỳ vọng (low 0–39 / mid 40–70 / high 71–100) theo **bằng chứng hiểu**, không theo độ khó câu hỏi.  
  - **Q2 Move:** `teaching_strategy` khớp rule với (score, confidence, misconceptions).  
  - **Q3 Follow-up:** khi score &lt; 90 hoặc có misconception → đúng 1 câu hỏi (có `?`).  
  - **Q4 Misconception trung thực:** expect_empty=true → phải `[]`; expect_empty=false → phải ≥1.  
  - Case pass = Q1 ∧ Q2 ∧ Q3 ∧ Q4.

- **Golden set:** 22 case trong [`eval/golden-set.jsonl`](eval/golden-set.jsonl)  
  - ≥2 / mỗi lớp chỗ khó; 15 case từ chatlog (`source_turn` / `conversation_id`); đủ thường + hiếm.

- **Quality bar (CHỐT — giữ nguyên sau 23:59 N1):**  
  > **Đạt khi ≥70% case trong golden set pass (Q1∧Q2∧Q3∧Q4), VÀ 0 case bịa misconception** (case `expect_empty_misconceptions=true` mà hệ thống vẫn gán misconception).

- **Kết quả các lượt chạy** (cập nhật đến trước CP6):

| Run | Provider / model | LLM thật | Pass | vs bar | File |
|---|---|---|---|---|---|
| 1 | mock | 0/22 | 22/22 | n/a (scaffold) | `eval/results-run1.md` |
| 2 | gemini 3.5-flash | 5/22 | 21/22 | n/a (429 quota) | `eval/results-run2.md` |
| 3 | gemini-3.1-flash-lite | 22/22 | **16/22 = 72.7%** | CHƯA ĐẠT (bịa misc + nhãn) | `eval/results-run3.md` |
| 4 | gemini-3.1-flash-lite | 22/22 | 18/22 = 81.8% | CHƯA ĐẠT (Q4) | `eval/results-run4.md` |
| 5 | gemini-3.1-flash-lite | 22/22 | **21/22 = 95.5%** | **ĐẠT** | `eval/results-run5.md` |

- **Case fail còn lại (run 5):** G07 — HV dán nguyên văn slide; model cho high vì tưởng tự diễn đạt. Nguyên nhân: Context chưa có excerpt slide để phân biệt paste vs paraphrase. Hướng sửa CP5: truyền excerpt / topic_hint chặt hơn (đã ghi `eval/README.md`).

---

## §8. Phân công & kế hoạch

- **Phân công có tên:**

| Phần | Người phụ trách |
|---|---|
| Spec (`spec.md`) | Ngô Hùng Phúc — 2A202601069 |
| Evidence / mining | Nguyễn Văn Linh — 2A202601971 |
| Prompt + Estimator / Misconception | Nguyễn Duy Hoàng — 2A202601147 |
| Strategy + Follow-up + `codebase/` UI | Nguyễn Ngọc Dương — 2A202601717 |
| Eval golden set + results | Lê Văn Long — 2A20261711 |
| Demo slides + dry run | Ngô Hùng Phúc — 2A202601069 (lead) · cả nhóm hỗ trợ |
| Validation log (CP5) | Nguyễn Văn Linh — 2A202601971 (log) · cả nhóm tuyển user |

- **Willing users (≥3 tên)** *(tuyển HV ngoài nhóm trước CP5 — chưa chốt tên):* _[HV ngoài 1]_, _[HV ngoài 2]_, _[HV ngoài 3]_  
- **Kế hoạch validation CP5 — 3 câu hỏi, ai log:**  
  1. Sau câu trả lời, bạn có hiểu mình đang đứng ở mức hiểu nào không?  
  2. Câu hỏi follow-up có giúp bạn tự kiểm tra không, hay chỉ làm phiền?  
  3. Có lúc nào bạn thấy hệ thống gán hiểu lầm oan không?  
  → Nguyễn Văn Linh log nguyên văn vào `validation/feedback-log.md` (≥5 mẩu từ ≥5 người ngoài nhóm).

- **Multi-prototype:** Không tách 2 UI. Trục đã thử nội bộ: follow-up **template** vs **LLM** → chọn LLM cho chat (chất lượng câu hỏi), giữ template cho eval/Flow Lab golden-hit để ổn định quota.

---

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| CP2 | Scaffold Streamlit + rules strategy | Cần flow bấm được trước LLM |
| CP3 run3 | Đo LLM thật 16/22 | Baseline; lộ nhãn band mơ hồ + bịa misconception |
| CP3 run4–5 | Relabel golden theo bằng chứng hiểu; siết prompt misconception; bỏ nới band | Run3/4 fail Q1/Q4; đạt bar ở run5 (21/22) |
| Sau CP3 | Follow-up chuyển sang Gemini (+ template fallback); UI sáng + khung chat cuộn; Flow Lab cache→golden→API | Câu hỏi phụ máy móc; cần trace nguồn dữ liệu khi demo |
| CP4 | Chốt `spec.md` + quality bar ≥70% & 0 bịa misconception | Hạn cứng CP4 / 23:59 N1 |

---

## Phụ lục nhanh — Quyết định AI trung tâm (cho form CP3/CP4)

> AI quyết định học viên đã hiểu khái niệm đến mức nào (`understanding_score` 0–100 + misconception?) để chọn teaching move và sinh câu hỏi kiểm tra — dùng **gemini-3.1-flash-lite**.
