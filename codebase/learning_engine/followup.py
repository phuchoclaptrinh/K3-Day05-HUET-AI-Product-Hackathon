from __future__ import annotations

import re

from .context import ConversationContext
from .llm_client import call_llm_json, resolve_mode

SYSTEM_PROMPT = """Bạn là chuyên gia sư phạm AI Tutor (VLearn).
Nhiệm vụ: sinh ĐÚNG 1 câu hỏi follow-up tiếng Việt để kiểm tra / củng cố mức hiểu của học viên.

Trả JSON:
{
  "follow_up": "<1 câu hỏi kết thúc bằng ?>",
  "intent": "check|example|repair|clarify|advance"
}

Quy tắc:
- Câu hỏi ngắn, rõ, có thể trả lời trong 1–3 câu.
- Bám đúng teaching_strategy và misconception (nếu có).
- Không hỏi lại nguyên văn câu học viên vừa hỏi.
- Không làm bài hộ / không xin đáp án dài.
- Nếu học viên mới xin tóm tắt/định nghĩa → hỏi để họ tự nói lại ý chính.
- Nếu có misconception → hỏi buộc họ phân biệt / sửa chỗ sai cụ thể.
- Nếu score cao (≥90) → hỏi nhẹ để xác nhận hoặc gợi ý bước tiếp.
"""


def _topic_phrase(ctx: ConversationContext) -> str:
    if ctx.topic_hint:
        return ctx.topic_hint[:80]
    text = ctx.student_latest
    text = re.sub(r"^\(Trang[^)]*\)\s*", "", text).strip()
    text = re.sub(r'^"[^"]+"\s*', "", text).strip()
    if len(text) > 80:
        text = text[:77] + "..."
    return text or "khái niệm vừa hỏi"


def _normalize_question(text: str) -> str:
    q = re.sub(r"\s+", " ", (text or "").strip())
    q = q.strip("\"'`")
    if not q:
        return ""
    if not q.endswith("?"):
        q = q.rstrip(".!") + "?"
    return q


def _template_followup(
    ctx: ConversationContext,
    teaching_strategy: str,
    misconceptions: list[str],
    understanding_score: int,
) -> str:
    topic = _topic_phrase(ctx)
    misc = misconceptions[0] if misconceptions else None

    if misc:
        return (
            f"Bạn hãy giải thích lại bằng lời của mình để sửa: {misc} — đâu là điểm đúng?"
        )
    if teaching_strategy == "review_concept":
        return f"Bạn hãy giải thích lại bằng lời của mình: {topic}?"
    if teaching_strategy == "give_example":
        return f"Thử áp dụng vào một ví dụ ngắn: với «{topic}», bạn sẽ làm thế nào?"
    if teaching_strategy == "validate_understanding":
        return f"Theo bạn, ý chính của «{topic}» là gì — nói trong 1–2 câu?"
    if teaching_strategy == "give_hint":
        return f"Gợi ý: bắt đầu từ định nghĩa cốt lõi của «{topic}» — bạn thử bước tiếp?"
    if teaching_strategy == "next_topic":
        return f"Phần «{topic}» có vẻ ổn — bạn muốn sang khái niệm liên quan tiếp theo không?"
    if understanding_score < 90:
        return f"Trước khi sang ý mới, bạn tự kiểm tra nhanh: {topic}?"
    return f"Bạn muốn đào sâu thêm «{topic}» hay chuyển chủ đề?"


def generate_followup(
    ctx: ConversationContext,
    teaching_strategy: str,
    misconceptions: list[str],
    understanding_score: int,
    understanding_reason: str = "",
    confidence: str = "medium",
) -> tuple[list[str], str]:
    """Return ([follow_up], provider). LLM-first, template fallback."""
    mode = resolve_mode()
    if mode != "mock":
        user = f"""TOPIC_HINT: {ctx.topic_hint or "(không có)"}
STUDENT_LATEST: {ctx.student_latest}
HISTORY:
{ctx.history_text() or "(trống)"}

UNDERSTANDING_SCORE: {understanding_score}
CONFIDENCE: {confidence}
REASON: {understanding_reason or "(không có)"}
MISCONCEPTIONS: {misconceptions or []}
TEACHING_STRATEGY: {teaching_strategy}
"""
        try:
            data, provider = call_llm_json(SYSTEM_PROMPT, user)
            question = _normalize_question(str(data.get("follow_up") or ""))
            if question:
                return [question], provider
        except Exception:
            pass

    return [
        _template_followup(ctx, teaching_strategy, misconceptions, understanding_score)
    ], "template"
