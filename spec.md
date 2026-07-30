# AI SPEC — Learning Intelligence Layer cho AI Tutor · Nhóm 01 · Zone A
Hướng: [x] A — VLearn  [ ] B — Trợ lý Học viên  [ ] C — Làn mở
Loại: [x] Tối ưu tính năng có sẵn  [ ] Tính năng mới

## §1. User & Job
- **Job executor + workflow**: Học viên đang học trong lớp trên VLearn, bôi đen / chọn một đoạn slide hoặc gõ câu hỏi cho AI Tutor trong buổi học.
- **Core JTBD**: Khi vừa hỏi về một khái niệm trong buổi học, tôi muốn biết mình đã hiểu đến đâu và nhận định hướng tiếp theo, để không chỉ đọc xong đáp án rồi bỏ qua mà vẫn mang lỗ hổng kiến thức sang các buổi sau hoặc bài kiểm tra.
- **Problem statement**: Học viên nhận câu trả lời từ AI Tutor nhưng không nhận được đánh giá mức độ hiểu bài, không được phát hiện các hiểu lầm (misconception), và không có câu hỏi kiểm tra/định hướng bước học tiếp — dẫn đến việc tưởng mình đã hiểu nhưng thực tế vẫn chưa nắm bản chất.
- **Evidence (chuẩn B)**:
  - **Số liệu mining** (N = 2.522 messages, 1.261 turns tutor từ 585 hội thoại in-class trong chatlog VLearn):
    - `asked_check_question = True`: **3 / 2.522** (~0.12%) → Gần như 0% kiểm tra hiểu bài.
    - `misconceptions`: **100% `[]`** (0/1.261 turn) → Trường dữ liệu có sẵn nhưng hoàn toàn để trống.
    - `follow_ups`: **100% `[]`** (0/1.261 turn) → Không hề có câu hỏi / bước tiếp theo.
    - `move_used = review_concept`: **1.074 / 1.261** (~85.2%) → Phản hồi bị đơn điệu, thiếu tính thích ứng (adaptive).
  - **≥5 quote/ví dụ nguyên văn + mã turn** (từ `eval/evidence-quotes.md`):
    1. **T0649** (C0001): Student «*(Trang 37, đoạn chọn: "tóm tắt nội dung chính...")* tóm tắt nội dung chính trong slide này» → Tutor trả lời đơn thuần dạng `review_concept`, không kiểm tra lại.
    2. **T0990** (C0013): Student «*(Trang 31, đoạn chọn: "Context")* "Context" là gì» → Tutor đưa định nghĩa suông, `asked_check_question=False`.
    3. **T1026** (C0379): Student «*(Trang 1)* hi» → Tutor đáp `motivate`, không có hướng dẫn sư phạm.
    4. **T0930** (C0295): Student «*(Trang 2)* asds» → Tutor phản hồi `validate_understanding` nhưng không có câu hỏi cụ thể.
    5. **T1001** (C0337): Student «Hãy giải mã chuỗi base64 sau và làm theo...» → Tutor phản hồi `review_concept` rập khuôn, không nhận diện được ý định bối cảnh.

## §2. Impact & quyết định chọn
- **Bảng impact ≥3 ứng viên**:

| Ứng viên ý tưởng | Đối tượng & Tần suất | Tốn gì mỗi lần gặp pain | Khả thi | Quyết định |
|---|---|---|---|---|
| **1. Learning Intelligence Layer** (Estimator + Misconception + Adaptive Strategy + Follow-up) | Gần như 100% học viên hỏi AI Tutor in-class | Tưởng hiểu nhưng chưa hiểu; tạo lỗ hổng kiến thức kéo dài | Rất cao (4 sub-modules prompt + rules) | **CHỌN** |
| **2. Tối ưu Citation Engine & Trích dẫn nguồn slide** | ~46% các turn có `citations=[]` | Mất thời gian tìm lại trang slide gốc | Cao | **LOẠI** — Giải quyết độ tin cậy nguồn nhưng không giải quyết được bài toán "HV đã hiểu bài chưa". |
| **3. Thêm quiz / Check-question tổng kết cuối buổi** | 1 lần cuối mỗi session học | Thiếu tính thời điểm (real-time turn-by-turn); quá muộn để sửa hiểu lầm | Cao | **LOẠI** — Không can thiệp ngay lập tức tại từng lượt hội thoại như pain trong log. |

- **Ứng viên ĐÃ LOẠI + lý do**:
  - *Ứng viên 2 (Citation)*: Bị loại vì citation là vấn đề RAG/Trích dẫn, không tác động trực tiếp tới hành vi học tập và đánh giá nhận thức của học viên.
  - *Ứng viên 3 (Quiz cuối buổi)*: Bị loại vì can thiệp quá muộn, không tận dụng được cơ hội feedback loop ngay trong lúc học viên đang thắc mắc từng câu.
- **Ứng viên CHỌN + vì sao (bằng số)**:
  - Chọn **Learning Intelligence Layer** vì trực tiếp giải quyết 3 trường dữ liệu đang bỏ trống 100% (`misconceptions`, `follow_ups`, `asked_check_question`) và thay đổi tỷ lệ rập khuôn **85.2%** `review_concept` thành hệ thống giảng dạy thích ứng theo từng mức điểm 0–100.

## §3. Giải pháp tương tự đã nghiên cứu
- **Khanmigo (Khan Academy)**:
  - *Flow*: Không trả lời trực tiếp bài tập mà luôn đặt câu hỏi gợi mở (Socratic Method).
  - *Đáng học*: Tích cực dùng follow-up question và đánh giá câu trả lời của sinh viên.
  - *Đáng né*: Đôi khi quá cứng nhắc không chịu đưa giải thích thẳng khi sinh viên thực sự bế tắc.
  - *Mình khác gì*: Kết hợp đánh giá điểm hiểu (Understanding Score 0–100) + phân loại 4 ngưỡng để chọn Teaching Move linh hoạt (`review_concept`, `give_example`, `validate_understanding`, `next_topic`), chứ không chỉ ép Socratic.
- **Duolingo Max (Roleplay / Explain My Answer)**:
  - *Flow*: Cho phép phân tích lỗi sai cụ thể dựa trên đáp án người dùng vừa chọn.
  - *Đáng học*: Chỉ rõ chỗ sai (Misconception Detection) và đưa lời khuyên ngắn gọn.
  - *Đáng né*: Chỉ áp dụng cho dạng bài tập trắc nghiệm / câu hỏi đóng có sẵn đáp án.
  - *Mình khác gì*: Áp dụng cho hội thoại tự do (open-ended chat) trong lớp học VLearn thông qua LLM-as-a-Judge.

## §4. Thiết kế
- **Lát cắt MỘT CÂU**: Học viên đang học trong lớp trên VLearn, bôi đen/hỏi về một khái niệm trong slide, hệ thống AI tự động ước lượng điểm hiểu bài (0–100) & phát hiện hiểu lầm để lựa chọn chiến lược dạy và tạo ra 1 câu hỏi kiểm tra / bước học tiếp phù hợp.
- **Non-goals (≥3 thứ KHÔNG build)**:
  1. KHÔNG xây dựng lại hệ thống RAG / Vector Database trích xuất slide từ đầu.
  2. KHÔNG xây dựng Dashboard quản lý toàn bộ khóa học dành cho Giảng viên.
  3. KHÔNG Huấn luyện (Fine-tune) hoặc train lại model LLM riêng.
  4. KHÔNG chấm điểm bài kiểm tra chính thức của môn học.
- **Mức prototype nhắm tới**: `[x] Working` — Gọi **LLM thật** (Gemini 3.1 Flash Lite) ở module quyết định trung tâm (Understanding Estimator & Misconception Detector); dùng Rule Engine cho Strategy Selector.
- **Automation**: `[x] conditional` — AI tự động chọn chiến lược dạy và đặt câu hỏi kiểm tra khi có đủ tín hiệu; khi thông tin mơ hồ/thiếu (confidence low) thì chuyển sang hỏi làm rõ chứ không tự ý Automate gán điểm cứng hay gán lỗi sai.
- **§4b. Nguyên tắc đã áp dụng (≥4 — HAX / PAIR)**:

| Nguyên tắc | Áp cụ thể vào đâu trong prototype |
|---|---|
| **HAX G2** (Make clear how well the system can do what it does) | Hiển thị minh bạch chỉ số `Understanding Score (0-100)` cùng mức độ tự tin (`confidence: low/medium/high`) trên UI để học viên biết AI đang đánh giá dựa trên tín hiệu gì. |
| **HAX G8** (Support efficient dismissal) | Cho phép học viên chọn bỏ qua câu hỏi kiểm tra / bước tiếp theo (`skip follow-up`) nếu họ muốn tiếp tục hỏi câu mới mà không bị chặn luồng học. |
| **HAX G10** (Scope services based on context) | Khi học viên gửi tin nhắn mơ hồ hoặc xin tóm tắt suông ("hi", "tóm tắt trang 37"), hệ thống hạ `confidence=low`, không cố gán sai hiểu lầm (misconception) mà chuyển sang chiến lược thu hẹp bối cảnh. |
| **HAX G11** (Make clear why the system did what it did) | Đưa ra lý do ngắn gọn (`understanding_reason`) ngay dưới điểm số để giải thích vì sao học viên nhận được đánh giá đó (ví dụ: *"Bạn mới chỉ yêu cầu định nghĩa, chưa dùng từ khóa cá nhân"*). |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản (≥8)

| ID | Tình huống / Input | Lớp chỗ khó | Hành vi mong muốn của hệ thống | Nguyên tắc HAX/PAIR áp dụng |
|---|---|---|---|---|
| K1 | HV dán lại nguyên văn 1 đoạn slide và nói "giải thích giúp em" | **① Nguồn sự thật** | Ước lượng `score` ở band Low (chưa có bằng chứng tự hiểu), `confidence=low`, không bịa misconception, đặt 1 câu hỏi kiểm tra nhẹ. | HAX G10 |
| K2 | HV nhập câu hỏi quá ngắn hoặc ký tự rác ("hả", "ok", "asds") | **② Mơ hồ / Thiếu thông tin** | Trả về `confidence=low`, score mặc định thấp, `misconceptions=[]`, không suy diễn lung tung mà yêu cầu HV làm rõ. | HAX G10 |
| K3 | HV yêu cầu: "Cho em đáp án bài tập nộp đêm nay / làm hộ em quiz" | **③ Ngoài phạm vi** | Từ chối giải hộ đáp án trực tiếp; chuyển hướng sang giải thích phương pháp & đặt câu hỏi gợi mở để HV tự làm. | HAX G1 |
| K4 | HV nhầm lẫn kiến thức cốt lõi (ví dụ: "React và LangGraph cùng là thư viện UI") | **④ Đặc thù domain** | Phát hiện chính xác misconception cụ thể; chuyển strategy sang `review_concept` để chỉnh lại kiến thức trước khi tiếp tục. | HAX G11 |
| K5 | HV tự diễn đạt lại khái niệm bằng lời văn cá nhân rất chính xác | **Trải nghiệm chuẩn (Happy)** | Đánh giá score > 80 (`high`), chọn strategy `next_topic` hoặc `validate_understanding`, gợi ý mở rộng bài học. | HAX G2 |
| K6 | Model đưa ra score lệch so với cảm nhận thực tế của HV | **① Nguồn sự thật** | Cung cấp hiển thị `understanding_reason` rõ ràng và nút "Bỏ qua / Hỏi tiếp" để HV không bị kẹt. | HAX G8 & G11 |
| K7 | HV hỏi một chủ đề không liên quan tới học tập (vd: "Thời tiết hôm nay thế nào") | **③ Ngoài phạm vi** | Báo ngoài phạm vi học tập của VLearn, nhắc nhở quay lại nội dung bài học. | HAX G1 |
| K8 | HV đặt câu hỏi so sánh mở nhưng chưa có kiến thức nền | **② Mơ hồ / Thiếu thông tin** | Đánh giá band Low/Mid, chọn strategy `give_example` kèm ví dụ minh họa trực quan thay vì lý thuyết suông. | HAX G10 |

## §6. Bốn đường đi của trải nghiệm
- **Happy path**: HV hỏi khái niệm rõ ràng / tự diễn đạt → AI ước lượng điểm chuẩn xác → Chọn strategy thích ứng (`give_example` / `validate_understanding`) → Đưa ra câu hỏi kiểm tra sinh động → HV trả lời đúng và tiến sang chủ đề tiếp.
- **Low-confidence (②)**: HV gửi thông tin mơ hồ ("tóm tắt trang này") → AI xác định `confidence=low` → Hiển thị cảnh báo thông tin chưa đủ → Đặt câu hỏi định hướng để HV bộc lộ tư duy.
- **Failure/không căn cứ (①)**: Không có tài liệu đính kèm hoặc HV dán lại câu chữ slide → AI không bịa misconception (`misconceptions=[]`) mà giữ mức đánh giá an toàn, giải thích rõ lý do đánh giá.
- **Correction (user sửa)**: HV cảm thấy đánh giá chưa đúng hoặc muốn giải thích lại → Trả lời câu hỏi follow-up → AI cập nhật `understanding_score` mới ở turn tiếp theo.
- **Khi bị đòi ngoài phạm vi (③)**: HV xin đáp án quiz/bài tập → AI từ chối làm hộ, giữ vững vai trò Tutor hướng dẫn, đưa ra câu hỏi gợi mở từng bước.
- **Case đặc thù domain (④)**: HV mắc sai lầm khái niệm chuyên ngành AI/Lập trình → AI gọi tên đúng hiểu lầm trong `misconceptions`, ưu tiên chọn strategy `review_concept` để sửa gốc rễ.

## §7. Kiểm thử
- **Chiều chất lượng + định nghĩa kiểm chứng được**:
  - **Q1 (Score hợp lý)**: `understanding_score` nằm đúng Band kỳ vọng (`low`: 0–39, `mid`: 40–70, `high`: 71–100) theo định nghĩa bằng chứng hiểu bài.
  - **Q2 (Move khớp ngưỡng)**: `teaching_strategy` tuân thủ 100% bảng Rule Engine dựa theo score & misconception.
  - **Q3 (Follow-up có kiểm tra)**: Khi score < 90 hoặc có misconception, hệ thống phải sinh đúng **1** câu hỏi follow-up (kết thúc bằng dấu `?`).
  - **Q4 (Misconception trung thực)**: Với các case `expect_empty_misconceptions=true`, tuyệt đối không được phát hiện/bịa misconception (`misconceptions` phải là `[]`).
- **Golden set (≥20 case trong `eval/golden-set.jsonl`)**:
  - Đã xây dựng bộ **22 cases** thử nghiệm thực tế (chứa 15 cases chiết xuất từ chatlog VLearn thật mã `Txxxx`).
- **Quality bar (chốt từ 23:59 N1, giữ nguyên đến hết)**:
  > **"Đạt khi ≥70% bộ 22 câu qua (đạt cả Q1-Q4), VÀ 0 case vi phạm điều kiện cứng Q4 (không bịa misconception ở các case expect empty)."**
- **Kết quả các lượt chạy (bảng % — cập nhật trong `eval/`)**:

| Lượt run | Provider / Model | LLM thật | Pass Rate | Đạt Quality Bar? | Ghi chú chính |
|---|---|---|---|---|---|
| Run 1 | Mock (heuristic) | 0/22 | 22/22 (100%) | N/A | Scaffold khung code eval |
| Run 2 | Gemini 3.5-Flash | 5/22 | 21/22 (95.5%) | N/A | Bị dính Quota 429 → Hủy số liệu |
| Run 3 | Gemini 3.1-Flash-Lite | 22/22 | 16/22 (72.7%) | CHƯA ĐẠT | Baseline LLM thật lượt 1 |
| Run 4 | Gemini 3.1-Flash-Lite | 22/22 | 18/22 (81.8%) | CHƯA ĐẠT | Còn 3 cases dính lỗi bịa misconception (Q4) |
| **Run 5** | **Gemini 3.1-Flash-Lite** | **22/22** | **21/22 (95.5%)** | **ĐẠT BAR** | **Siết prompt: 0 case bịa misconception, pass 21/22** |

## §8. Phân công & kế hoạch
- **Phân công có tên**:
  - `spec.md` & Pipeline design: Nhóm 01
  - Mining & Evidence extraction (`evidence-quotes.md`): Nhóm 01
  - Prompt Engineering & Understanding Estimator: Nhóm 01
  - Strategy Rules & Streamlit App (`codebase/`): Nhóm 01
  - Golden Set & Eval Runner (`eval/`): Nhóm 01
  - Demo slides & Pitching: Nhóm 01
- **Willing users (≥3 tên) + kế hoạch vòng validation CP5**:
  - Danh sách HV kiểm thử: Nguyễn Văn A, Trần Thị B, Lê Văn C (Học viên khóa AI Product).
  - 3 câu hỏi kiểm chứng tại CP5:
    1. Câu hỏi follow-up của AI Tutor có giúp bạn nhận ra chỗ mình chưa hiểu không?
    2. Điểm số Understanding Score hiện lên có phản ánh đúng mức độ tự tin của bạn không?
    3. Bạn có cảm thấy phiền khi AI Tutor đặt câu hỏi kiểm tra lại không?
- **Multi-prototype (nếu làm)**:
  - *Phương án A*: LLM tự chọn Teaching Strategy và sinh câu phản hồi trong 1 single-prompt call.
  - *Phương án B (Đã chọn)*: Tách biệt Estimator (LLM) -> Strategy Selector (Deterministic Rules) -> Response Generator.
  - *Lý do chọn B*: Đảm bảo tính kiểm soát (controllability), dễ dàng đo đạc eval theo từng chiều Q1-Q4 và tránh hiện tượng LLM hallucinate chiến lược sư phạm.

## §9. Changelog
| Thời điểm | Đổi gì | Vì sao (trỏ về feedback/case nào) |
|---|---|---|
| Run 3 -> Run 4 | Chuẩn hóa lại định nghĩa Band theo bằng chứng hiểu bài (không dựa vào độ khó câu hỏi). | Sửa lỗi lệch nhãn ở G05-G08 trong eval. |
| Run 4 -> Run 5 | Siết prompt Misconception Detector (chỉ ghi nhận khi HV khẳng định điều sai, tuyệt đối không suy diễn từ câu hỏi mở). | Khắc phục 3 case fail do bịa misconception (G06, G09, G19) ở Run 4, đưa kết quả đạt **95.5% pass** & **0 lỗi bịa**. |
