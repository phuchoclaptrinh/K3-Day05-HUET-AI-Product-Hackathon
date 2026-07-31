from __future__ import annotations

import re

from .context import ConversationContext
from .estimator import EstimateResult
from .example import ExampleIllustration
from .followup import CheckQuestion
from .llm_client import call_llm_text, resolve_mode
from .strategy import StrategyResult

STRATEGY_GUIDE = {
    "review_concept": (
        "Ôn lại đúng 1–2 ý cốt lõi, ngắn gọn; nếu có misconception thì sửa chỗ đó trước."
    ),
    "give_example": (
        "Cho 1 ví dụ rất ngắn gắn với câu hỏi của học viên, rồi rút ra bài học."
    ),
    "validate_understanding": (
        "Đừng giảng dài. Tóm tắt tối đa 2 câu rồi dừng — câu trắc nghiệm sẽ được hệ thống gắn sau."
    ),
    "give_hint": (
        "Đưa 1 gợi ý định hướng, không đưa đáp án đầy đủ."
    ),
    "next_topic": (
        "Xác nhận học viên đã nắm khá tốt; gợi ý bước tiếp theo nhẹ nhàng."
    ),
}


def _strip_trailing_open_questions(text: str) -> str:
    """Gỡ câu hỏi tự luận mà model hay tự bịa ở cuối."""
    text = (text or "").rstrip()
    # Cắt block kiểu "Theo bạn, ... ?" / "Bạn hãy giải thích... ?"
    patterns = [
        r"(?:\n|^)\s*(?:Theo bạn|Bạn hãy|Hãy giải thích|Em hãy|Bạn thử nói).*?\?\s*$",
        r"(?:\n|^)\s*\*\*Câu hỏi.*$",
    ]
    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE | re.DOTALL).rstrip()
    return text


def _mcq_block(check: CheckQuestion) -> str:
    lines = [
        "---",
        "### Câu hỏi kiểm tra (trắc nghiệm)",
        check.question,
        "",
    ]
    for key in ("A", "B", "C", "D"):
        if key in check.options:
            lines.append(f"**{key}.** {check.options[key]}")
    lines.append("")
    lines.append("_Chọn đáp án A/B/C/D ở panel bên phải để cập nhật mức hiểu bài._")
    return "\n".join(lines)


def generate_tutor_response(
    ctx: ConversationContext,
    estimate: EstimateResult,
    strategy: StrategyResult,
    follow_ups: list[str],
    check_question: CheckQuestion | None = None,
    example: ExampleIllustration | None = None,
    take_note: str = "",
) -> tuple[str, str]:
    """Return (tutor_response, provider). Gắn take-note (nếu ngoài bài) + ví dụ + MCQ."""
    mode = resolve_mode()
    guide = STRATEGY_GUIDE.get(strategy.teaching_strategy, "Dạy đúng mức hiểu hiện tại.")

    body = ""
    provider = "template"

    if mode != "mock":
        try:
            external_flag = (
                "Câu hỏi hơi lệch transcript buổi học — giải thích ngắn, "
                "nêu rõ đây là kiến thức bổ sung ngoài bài nếu cần.\n"
                if take_note
                else ""
            )
            system = (
                "Bạn là AI Tutor VLearn trong lớp học. Giọng sư phạm, tiếng Việt, đúng cỡ.\n"
                f"{external_flag}"
                "Bạn ĐƯỢC cung cấp LESSON_EXCERPT (nội dung buổi học). "
                "Giải thích bám excerpt + câu hỏi học viên; không bịa số trang ngoài excerpt.\n"
                "CHỈ viết phần giảng dạy (2–5 câu) theo teaching_strategy.\n"
                "CẤM viết câu hỏi cho học viên (cấm 'Theo bạn', 'Bạn hãy giải thích', "
                "'tại sao bạn nghĩ', câu hỏi mở bất kỳ).\n"
                "CẤM viết block 'Ví dụ minh họa', CẤM viết Take-note, CẤM viết đáp án A/B/C/D — "
                "hệ thống sẽ gắn các block đó sau.\n"
                "Không làm bài hộ. Không chào dài."
            )
            user = f"""STUDENT: {ctx.student_latest}
TOPIC_HINT: {ctx.topic_hint or "(không có)"}
HISTORY:
{ctx.history_text() or "(trống)"}

LESSON_CONTEXT:
{ctx.lesson_prompt()}

STRATEGY: {strategy.teaching_strategy}
STRATEGY_GUIDE: {guide}
UNDERSTANDING: {estimate.understanding_score}% ({estimate.confidence})
REASON: {estimate.understanding_reason}
MISCONCEPTIONS: {estimate.misconceptions or []}
"""
            body, provider = call_llm_text(system, user)
            body = _strip_trailing_open_questions(body)
        except Exception:
            body = ""
            provider = "template"

    if not body:
        body = _teaching_body(estimate, strategy)
        provider = "template" if provider != "gemini" else provider

    parts: list[str] = []
    if take_note:
        parts.append(take_note.strip())
    parts.append(body.strip())
    if example is not None:
        parts.append(example.markdown())
    if check_question is not None:
        parts.append(_mcq_block(check_question))
    elif follow_ups:
        parts.append(f"---\n### Câu hỏi kiểm tra\n{follow_ups[0]}")
    return "\n\n".join(parts), provider


def _teaching_body(estimate: EstimateResult, strategy: StrategyResult) -> str:
    move = strategy.teaching_strategy
    misc = estimate.misconceptions
    if move == "review_concept" and misc:
        return (
            f"Mình thấy có chỗ dễ nhầm: **{misc[0]}**. "
            "Hãy nắm đúng bản chất trước, rồi mới áp dụng."
        )
    if move == "review_concept":
        return (
            "Mình ôn lại ý cốt lõi: nắm định nghĩa → việc nó giải quyết → "
            "tránh nhầm với khái niệm gần."
        )
    if move == "give_example":
        return (
            "Để dễ hình dung, hãy gắn khái niệm vào một ví dụ ngắn rồi đối chiếu định nghĩa."
        )
    if move == "validate_understanding":
        return (
            "Tín hiệu hiểu còn mỏng. Mình tóm tắt ngắn, sau đó bạn làm một câu trắc nghiệm."
        )
    if move == "next_topic":
        return (
            f"Bạn đang thể hiện mức hiểu khá tốt (~{estimate.understanding_score}%). "
            "Củng cố nhẹ rồi có thể sang ý liên quan."
        )
    return "Mình sẽ hỗ trợ theo đúng mức hiểu hiện tại của bạn."


def _template_response(
    ctx: ConversationContext,
    estimate: EstimateResult,
    strategy: StrategyResult,
    follow: str,
) -> str:
    """Giữ API cũ cho flow_lab — nếu follow đã là MCQ text thì gắn nguyên."""
    body = _teaching_body(estimate, strategy)
    return f"{body}\n\n---\n### Câu hỏi kiểm tra (trắc nghiệm)\n{follow}".strip()
