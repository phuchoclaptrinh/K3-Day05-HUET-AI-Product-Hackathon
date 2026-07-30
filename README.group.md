# Learning Engine Tutor — Repo nhóm (Hackathon Batch 03)

**Hướng:** A — VLearn · tối ưu AI Tutor hiện có  
**Lát cắt:** Học viên đang học trong lớp · muốn biết mình đã hiểu khái niệm vừa hỏi chưa · hệ thống ước lượng mức hiểu + chọn teaching move · học viên nhận câu hỏi kiểm tra / bước học tiếp.

| Artifact chính | Path |
|---|---|
| AI Spec (CP4 · chốt 23:59 N1) | [`spec.md`](spec.md) |
| Pipeline triển khai | [`docs/00-pipeline-trien-khai.md`](docs/00-pipeline-trien-khai.md) |
| Canvas CP1 | [`docs/canvas-cp1.md`](docs/canvas-cp1.md) |
| Prototype | [`codebase/`](codebase/) |
| Evidence + golden + results | [`eval/`](eval/) |
| Validation (CP5) | [`validation/`](validation/) |

## Thành viên & phân công

| Mã HV | Tên | Phụ trách |
|---|---|---|
| 2A202601069 | Ngô Hùng Phúc | Spec · Demo slides (lead) |
| 2A202601971 | Nguyễn Văn Linh | Evidence / mining · Validation log (CP5) |
| 2A202601147 | Nguyễn Duy Hoàng | Prompt + Understanding Estimator / Misconception |
| 2A202601717 | Nguyễn Ngọc Dương | Strategy + Follow-up + `codebase/` UI |
| 2A20261711 | Lê Văn Long | Eval golden set + bảng kết quả |

## Chạy prototype

```bash
cd codebase
pip install -r requirements.txt
copy .env.example .env   # điền GEMINI_API_KEY
streamlit run app.py
```

Đo eval:

```bash
python eval/run_eval.py --run 6 --model gemini-3.1-flash-lite --sleep 5
```

## Checklist CP4 (chốt tiến độ)

- [x] Evidence chuẩn B + ≥5 quote (`eval/evidence-quotes.md`)
- [x] Bảng impact ≥3 + ứng viên loại (`spec.md` §2)
- [x] Lát cắt 1 câu + non-goals + Conditional (`spec.md` §4)
- [x] ≥4 HAX trỏ vào UI/module (`spec.md` §4b)
- [x] 4 lớp + ≥8 kịch bản (`spec.md` §5)
- [x] Golden ≥20 + quality bar số chốt (`spec.md` §7)
- [x] Bảng kết quả run 3–5 trung thực (`eval/results-run*.md`)
- [x] Điền tên thành viên / phân công vào `spec.md` §8 + README này
- [ ] Willing users ≥3 (HV **ngoài nhóm**) trước CP5
- [ ] Commit `spec.md` trước **23:59 ngày 1**

## Bảo mật data

- Không commit `data/**/*.csv` hay API key (`.env` đã gitignore).
- Golden/evidence chỉ dùng mã `Txxxx`/`Cxxxx` + trích ngắn.
