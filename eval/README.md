# Eval — định nghĩa chấm (kiểm chứng được)

File này là "luật chấm" để người ngoài nhóm chấm ra **cùng kết quả**. Chạy: `python eval/run_eval.py --run N`.

## Band của Understanding Score — chấm theo BẰNG CHỨNG HIỂU, không theo độ khó câu hỏi

Nguyên tắc gốc (project brief §7): điểm hiểu phản ánh việc học viên **có chứng minh được mình hiểu** hay không.

| Band | Khoảng | Đạt khi tin nhắn học viên… |
|---|---|---|
| `low` | 0–39 | **Chưa có bằng chứng hiểu**: xin tóm tắt / xin giải thích / hỏi định nghĩa, dán lại nguyên văn slide, greeting, input vô nghĩa, yêu cầu ngoài phạm vi, hoặc phát biểu sai kiến thức |
| `mid` | 40–70 | **Bằng chứng một phần**: mô tả tình huống cụ thể của mình, dùng đúng một phần thuật ngữ, nêu hiểu biết chưa đầy đủ |
| `high` | 71–100 | **Chứng minh được hiểu**: diễn đạt lại khái niệm bằng lời mình, so sánh có nội dung, hoặc kiểm chứng lại một phát biểu đúng |

Lưu ý quan trọng: **“hỏi một câu khó” không làm tăng band.** Học viên dán một đoạn slide phức tạp và nói “giải thích giúp em” vẫn là `low`, vì chưa có bằng chứng hiểu nào.

## Bốn chiều chất lượng

| # | Chiều | Pass khi |
|---|---|---|
| Q1 | Score hợp lý | Band của `understanding_score` **khớp đúng** band kỳ vọng trong golden set (khớp nghiêm ngặt, không nới) |
| Q2 | Move khớp ngưỡng | `teaching_strategy` đúng bảng rule §3.4 của pipeline với `(score, confidence, misconceptions)` thực tế |
| Q3 | Follow-up có kiểm tra | Khi `score < 90` hoặc có misconception → đúng **1** follow-up dạng câu hỏi (có `?`) |
| Q4 | Misconception trung thực | `expect_empty_misconceptions=true` → phải `[]`; `false` → phải phát hiện ≥1 |

**Case pass** = Q1 ∧ Q2 ∧ Q3 ∧ Q4.

## Quality bar (chốt tại `spec.md` 23:59 N1)

> Đạt khi **≥70% case pass** VÀ **0 case bịa misconception** (case `expect_empty=true` mà trả về misconception).

Điều kiện cứng thứ hai đứng riêng vì đây là lỗi đắt nhất: gán cho học viên một hiểu lầm họ không có sẽ khiến AI dạy sai hướng.

## Cơ cấu golden set (22 case)

| Nhóm | Case |
|---|---|
| Thường | G03–G11 (9) |
| ① Nguồn sự thật | G18, G19, G21 |
| ② Mơ hồ / thiếu thông tin | G01, G02, G12, G13 |
| ③ Ngoài phạm vi | G14, G15 |
| ④ Đặc thù domain | G16, G17, G20 |
| Hiếm | G22 |
| **Từ chatlog thật** | G01–G14, G21 (**15 case**, ghi `turn_id`/`conversation_id`) |

## Lịch sử các lượt đo

| Run | Provider / model | LLM thật | Pass | Bar | Ghi chú |
|---|---|---|---|---|---|
| 1 | mock (heuristic) | 0/22 | 22/22 = 100% | n/a | Scaffold trước khi có API key — **không tính cho CP3** |
| 2 | gemini `3.5-flash` | 5/22 | 21/22 = 95.5% | n/a | 17 case rơi fallback do `429` quota → **số liệu không dùng được** |
| 3 | gemini `3.1-flash-lite` | 22/22 | 16/22 = 72.7% | CHƯA ĐẠT | Baseline LLM thật đầu tiên; lộ ra nhãn band mơ hồ + bịa misconception |
| 4 | gemini `3.1-flash-lite` | 22/22 | 18/22 = 81.8% | CHƯA ĐẠT | Sau khi sửa nhãn band + chấm nghiêm ngặt. 3/4 fail là **bịa misconception** (vi phạm điều kiện cứng) |
| **5** | gemini `3.1-flash-lite` | 22/22 | **21/22 = 95.5%** | **ĐẠT** | Sau khi siết prompt misconception. 0 case bịa misconception |

## Changelog eval

| Sau run | Đổi gì | Vì sao |
|---|---|---|
| 3 | Viết lại định nghĩa band theo **bằng chứng hiểu**, relabel G05–G08, G10, G11 từ `mid` → `low` | Nhãn cũ gán `mid` cho các câu “xin giải thích khái niệm khó”, xung đột với chính rubric của nhóm. Hai người chấm độc lập lệch nhau → định nghĩa mơ hồ, phải viết lại (guide §2.6 bước 4) |
| 3 | Bỏ luật “nới band” trong `run_eval.py`, chuyển sang khớp band nghiêm ngặt | Luật nới làm điểm không kiểm chứng lại được bởi người ngoài nhóm |
| 4 | Siết prompt: chỉ ghi misconception khi học viên **khẳng định** điều sai; thêm danh sách trường hợp tuyệt đối không ghi (câu hỏi mở, thiếu kiến thức, ẩn dụ về cơ bản đúng); thêm bước tự kiểm “trích được chính xác câu nào?” | Run 4 có 3 case bịa misconception từ câu hỏi mở (G06, G09) và từ một phép ẩn dụ đúng (G19) — vi phạm điều kiện cứng của quality bar |
| 4 | Đưa thang điểm 3 band vào thẳng prompt | Model tự ý coi “câu hỏi khó” là dấu hiệu hiểu bài, lệch khỏi định nghĩa band của nhóm |

## Case còn fail sau run 5 — nguyên nhân gốc

**G07** (`turn_id=T0014`): học viên **dán lại nguyên văn** một đoạn key-takeaways từ slide rồi nhờ giải thích. Nhãn kỳ vọng là `low`; model cho **90 (`high`)** với lý do “học viên đã tự diễn đạt lại khái niệm cốt lõi”.

Nguyên nhân gốc: prototype hiện **chưa truyền nội dung slide** vào context, nên model không có cách nào phân biệt *dán lại tài liệu* với *tự diễn đạt bằng lời mình* — hai trường hợp có ý nghĩa sư phạm trái ngược nhau. Đây cũng chính là rủi ro lớp ① (nguồn sự thật) trong spec.

Hướng sửa (CP4/CP5): truyền `topic_hint` = excerpt đoạn học viên bôi đen vào Context Builder, và thêm luật “nếu tin nhắn trùng lặp cao với excerpt thì KHÔNG tính là bằng chứng hiểu”. Chưa làm trong CP3 để giữ lát cắt mỏng.

## Quan sát cần ghi vào spec

Phân bố teaching move ở run 5 nghiêng mạnh về `review_concept` (17/22) — **giống hệt** pain của VLearn hiện tại (~85% `review_concept`). Nguyên nhân: golden set cố tình nặng các câu mở đầu ít tín hiệu, còn adaptive teaching chỉ bộc lộ giá trị qua **nhiều turn liên tiếp**. Cần thêm case multi-turn (có `history`) để đo được sự chuyển dịch chiến lược, thay vì chỉ đo turn đơn.
