from __future__ import annotations

from .context import ConversationContext
from .estimator import EstimateResult
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
        "Đừng giảng dài. Tóm tắt tối đa 2 câu rồi chuyển sang câu hỏi kiểm tra."
    ),
    "give_hint": (
        "Đưa 1 gợi ý định hướng, không đưa đáp án đầy đủ."
    ),
    "next_topic": (
        "Xác nhận học viên đã nắm khá tốt; gợi ý bước tiếp theo nhẹ nhàng."
    ),
}


def generate_tutor_response(
    ctx: ConversationContext,
    estimate: EstimateResult,
    strategy: StrategyResult,
    follow_ups: list[str],
) -> tuple[str, str]:
    """Return (tutor_response, provider)."""
    follow = follow_ups[0] if follow_ups else ""
    mode = resolve_mode()
    guide = STRATEGY_GUIDE.get(strategy.teaching_strategy, "Dạy đúng mức hiểu hiện tại.")

    if mode != "mock":
        try:
            system = (
                "Bạn là AI Tutor VLearn trong lớp học. Giọng sư phạm, tiếng Việt, đúng cỡ.\n"
                "Cấu trúc bắt buộc:\n"
                "1) 2–5 câu dạy theo teaching_strategy\n"
                "2) Một câu chuyển tiếp ngắn\n"
                "3) Kết thúc bằng ĐÚNG câu follow-up được cung cấp (không sửa nội dung)\n\n"
                "Không làm bài hộ. Không bịa số trang/trích dẫn nếu không có trong ngữ cảnh. "
                "Không lặp lại nguyên văn câu hỏi học viên. Không mở đầu bằng lời chào dài."
            )
            user = f"""STUDENT: {ctx.student_latest}
TOPIC_HINT: {ctx.topic_hint or "(không có)"}
HISTORY:
{ctx.history_text() or "(trống)"}

STRATEGY: {strategy.teaching_strategy}
STRATEGY_GUIDE: {guide}
UNDERSTANDING: {estimate.understanding_score}% ({estimate.confidence})
REASON: {estimate.understanding_reason}
MISCONCEPTIONS: {estimate.misconceptions or []}
FOLLOW_UP_MUST_END_WITH: {follow}
"""
            text, provider = call_llm_text(system, user)
            if follow and follow not in text:
                text = text.rstrip() + "\n\n" + follow
            return text, provider
        except Exception:
            pass

    return _template_response(ctx, estimate, strategy, follow), "template"


def _template_response(
    ctx: ConversationContext,
    estimate: EstimateResult,
    strategy: StrategyResult,
    follow: str,
) -> str:
    move = strategy.teaching_strategy
    misc = estimate.misconceptions

    if move == "review_concept" and misc:
        body = (
            f"Mình thấy có chỗ dễ nhầm: **{misc[0]}**. "
            "Hãy tách khái niệm cho rõ: nắm đúng bản chất trước, rồi mới áp dụng."
        )
    elif move == "review_concept":
        body = (
            "Mình ôn lại ý cốt lõi theo đúng phần bạn đang hỏi: "
            "nắm định nghĩa → xem nó giải quyết việc gì → tránh nhầm với khái niệm gần."
        )
    elif move == "give_example":
        body = (
            "Để dễ hình dung, hãy lấy một ví dụ ngắn gắn với câu hỏi của bạn, "
            "rồi đối chiếu lại định nghĩa — đừng chỉ nhớ câu chữ."
        )
    elif move == "validate_understanding":
        body = (
            "Phần này mình chưa chắc bạn đã nắm vững (tín hiệu hiểu còn mỏng). "
            "Trước khi giải thích dài, mình muốn bạn tự nói lại ý chính."
        )
    elif move == "next_topic":
        body = (
            f"Bạn đang thể hiện mức hiểu khá tốt (~{estimate.understanding_score}%). "
            "Có thể củng cố nhẹ rồi chuyển sang ý liên quan."
        )
    else:
        body = "Mình sẽ hỗ trợ theo đúng mức hiểu hiện tại của bạn."

    bridge = "Trước khi sang ý tiếp theo:"
    return f"{body}\n\n{bridge}\n{follow}".strip()
