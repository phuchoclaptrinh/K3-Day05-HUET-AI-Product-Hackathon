# -*- coding: utf-8 -*-
"""Đếm lại chỉ số pain từ chatlog (chuẩn evidence B). Không ghi nguyên CSV ra repo."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv"
OUT = ROOT / "eval/evidence-quotes.md"


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    n = len(rows)
    tutors = [r for r in rows if r["role"] == "tutor"]
    students = [r for r in rows if r["role"] == "student"]

    moves = Counter((r.get("move_used") or "").strip() or "(empty)" for r in tutors)
    misc_empty = sum(1 for r in tutors if (r.get("misconceptions") or "").strip() in {"", "[]"})
    follow_empty = sum(1 for r in tutors if (r.get("follow_ups") or "").strip() in {"", "[]"})
    check_true = sum(1 for r in rows if str(r.get("asked_check_question")).lower() == "true")

    # Pick short illustrative student quotes (ids only + truncated)
    quote_ids = ["T0649", "T0990", "T1026", "T0930", "T1001"]
    by_turn: dict[str, dict] = {}
    for r in rows:
        by_turn.setdefault(r["turn_id"], {})[r["role"]] = r

    lines = [
        "# Evidence mining — VLearn chatlog (chuẩn B)",
        "",
        "## Phương pháp đếm",
        "",
        "1. Nguồn: `data/vlearn-pack/chatlog/chat_history_anonymized_for_hackathon.csv` (không commit file này vào repo nộp).",
        "2. Script: `scripts/mine_evidence.py` — đếm trên toàn bộ dòng; lọc `role=tutor` cho move/misconceptions/follow_ups.",
        "3. `asked_check_question` đếm trên mọi message.",
        "4. Người khác chạy lại script sẽ ra cùng số.",
        "",
        "## Số liệu",
        "",
        f"- Tổng messages: **{n}** (student={len(students)}, tutor={len(tutors)})",
        f"- `asked_check_question=True`: **{check_true}/{n}**",
        f"- Tutor turns có `misconceptions` rỗng/`[]`: **{misc_empty}/{len(tutors)}**",
        f"- Tutor turns có `follow_ups` rỗng/`[]`: **{follow_empty}/{len(tutors)}**",
        "",
        "### Phân bố `move_used` (tutor)",
        "",
    ]
    for k, v in moves.most_common():
        pct = round(100.0 * v / len(tutors), 1)
        lines.append(f"- `{k}`: {v} ({pct}%)")

    review = moves.get("review_concept", 0)
    lines += [
        "",
        f"**Nhận xét:** `review_concept` ≈ {round(100*review/len(tutors),1)}% tutor turns — teaching move gần như đơn điệu; "
        "misconceptions/follow_ups chưa được dùng; check-question gần như không có.",
        "",
        "## ≥5 ví dụ nguyên văn (rút gọn + mã turn)",
        "",
    ]
    for tid in quote_ids:
        parts = by_turn.get(tid, {})
        s = parts.get("student")
        if not s:
            continue
        content = s["content"].replace("\n", " ").strip()
        if len(content) > 220:
            content = content[:217] + "..."
        lines.append(
            f"- **{tid}** / {s['conversation_id']}: student «{content}» "
            f"— tutor move=`{(parts.get('tutor') or {}).get('move_used','')}`, "
            f"check={s.get('asked_check_question')}"
        )

    lines += [
        "",
        "## Kết luận pain (1 câu)",
        "",
        "Học viên nhận câu trả lời từ tutor nhưng hệ thống hầu như không ước lượng hiểu bài, "
        "không phát hiện misconception, không follow-up kiểm tra — tối ưu trả lời hơn là dạy.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
