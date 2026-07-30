from __future__ import annotations

import re

from .context import ConversationContext


def _topic_phrase(ctx: ConversationContext) -> str:
    if ctx.topic_hint:
        return ctx.topic_hint[:80]
    text = ctx.student_latest
    # strip slide prefix
    text = re.sub(r"^\(Trang[^)]*\)\s*", "", text).strip()
    text = re.sub(r'^"[^"]+"\s*', "", text).strip()
    if len(text) > 80:
        text = text[:77] + "..."
    return text or "khái niệm vừa hỏi"


def generate_followup(
    ctx: ConversationContext,
    teaching_strategy: str,
    misconceptions: list[str],
    understanding_score: int,
) -> list[str]:
    """Exactly one follow-up question for the prototype."""
    topic = _topic_phrase(ctx)
    misc = misconceptions[0] if misconceptions else None

    if misc:
        q = f"Bạn hãy giải thích lại bằng lời của mình để sửa: {misc} — đâu là điểm đúng?"
        return [q]

    if teaching_strategy == "review_concept":
        return [f"Bạn hãy giải thích lại bằng lời của mình: {topic}?"]

    if teaching_strategy == "give_example":
        return [f"Thử áp dụng vào một ví dụ ngắn: với «{topic}», bạn sẽ làm thế nào?"]

    if teaching_strategy == "validate_understanding":
        return [f"Theo bạn, ý chính của «{topic}» là gì — nói trong 1–2 câu?"]

    if teaching_strategy == "give_hint":
        return [f"Gợi ý: bắt đầu từ định nghĩa cốt lõi của «{topic}» — bạn thử bước tiếp?"]

    if teaching_strategy == "next_topic":
        return [
            f"Phần «{topic}» có vẻ ổn — bạn muốn sang khái niệm liên quan tiếp theo không?"
        ]

    # default
    if understanding_score < 90:
        return [f"Trước khi sang ý mới, bạn tự kiểm tra nhanh: {topic}?"]
    return [f"Bạn muốn đào sâu thêm «{topic}» hay chuyển chủ đề?"]
