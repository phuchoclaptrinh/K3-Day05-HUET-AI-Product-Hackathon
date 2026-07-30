from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .context import ConversationContext
from .llm_client import call_llm_json, resolve_mode

SYSTEM_PROMPT = """Bạn là chuyên gia sư phạm AI Tutor (VLearn).
Nhiệm vụ: sinh ĐÚNG 1 câu hỏi TRẮC NGHIỆM (multiple choice) tiếng Việt để kiểm tra mức hiểu.

Trả JSON đúng schema:
{
  "question": "<đề bài ĐÓNG, kết thúc bằng ?>",
  "options": {
    "A": "<đáp án A>",
    "B": "<đáp án B>",
    "C": "<đáp án C>",
    "D": "<đáp án D>"
  },
  "correct_option": "A|B|C|D",
  "explanation": "<1–2 câu giải thích vì sao đáp án đúng>",
  "intent": "check|example|repair|clarify|advance"
}

Quy tắc BẮT BUỘC:
- Đề bài phải là câu hỏi ĐÓNG (chọn 1 trong 4), KHÔNG phải câu tự luận.
- CẤM đề bài kiểu: "Theo bạn...", "Bạn hãy giải thích...", "Tại sao bạn nghĩ...", "Nêu ví dụ...".
- Đúng 4 lựa chọn A/B/C/D; chỉ 1 đáp án đúng; distractor hợp lý.
- Không lộ đáp án trong đề bài.
- Bám teaching_strategy và misconception (nếu có).
- Nếu có misconception → ít nhất 1 lựa chọn phản ánh đúng misconception đó.
"""


@dataclass
class CheckQuestion:
    question: str
    options: dict[str, str]
    correct_option: str
    explanation: str = ""
    intent: str = "check"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def prompt_text(self) -> str:
        """Text hiển thị cho HV — không gồm đáp án đúng."""
        lines = [self.question, ""]
        for key in sorted(self.options.keys()):
            lines.append(f"{key}. {self.options[key]}")
        lines.append("")
        lines.append("Hãy chọn một đáp án (A/B/C/D).")
        return "\n".join(lines)

    def stem_for_eval(self) -> str:
        return self.question if self.question.endswith("?") else self.question.rstrip(".!") + "?"


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


def _normalize_mcq(data: dict[str, Any]) -> CheckQuestion | None:
    question = _normalize_question(str(data.get("question") or data.get("follow_up") or ""))
    raw_opts = data.get("options") or {}
    if not isinstance(raw_opts, dict):
        return None
    options: dict[str, str] = {}
    for key in ("A", "B", "C", "D"):
        val = str(raw_opts.get(key) or "").strip()
        if not val:
            return None
        options[key] = val
    correct = str(data.get("correct_option") or "").strip().upper()
    if correct not in options:
        return None
    if not question:
        return None
    return CheckQuestion(
        question=question,
        options=options,
        correct_option=correct,
        explanation=str(data.get("explanation") or "").strip(),
        intent=str(data.get("intent") or "check").strip() or "check",
    )


def _template_check_question(
    ctx: ConversationContext,
    teaching_strategy: str,
    misconceptions: list[str],
    understanding_score: int,
) -> CheckQuestion:
    topic = _topic_phrase(ctx)
    misc = misconceptions[0] if misconceptions else None
    topic_l = topic.lower()

    # Template chuyên biệt vài khái niệm hay gặp
    if "mvp" in topic_l or "mvp" in ctx.student_latest.lower():
        return CheckQuestion(
            question="MVP (Minimum Viable Product) nghĩa đúng nhất là gì?",
            options={
                "A": "Sản phẩm hoàn thiện đầy đủ mọi tính năng trước khi ra mắt.",
                "B": "Phiên bản tối giản đủ dùng để kiểm chứng giả thuyết với người dùng thật.",
                "C": "Bản prototype chỉ để khoe ý tưởng, không cần người dùng thử.",
                "D": "Sản phẩm đã scale lớn và tối ưu chi phí dài hạn.",
            },
            correct_option="B",
            explanation="MVP là bản tối giản để học từ người dùng thật trước khi đầu tư lớn.",
            intent="check",
        )

    if misc:
        return CheckQuestion(
            question=f"Khi nói về «{topic}», phát biểu nào ĐÚNG hơn?",
            options={
                "A": "Hai khái niệm gần nhau thường dùng thay nhau được.",
                "B": "Cần nắm đúng điểm khác biệt cốt lõi trước khi áp dụng.",
                "C": "Chỉ cần nhớ tên thuật ngữ là đủ.",
                "D": "Hiểu sai nhẹ không sao vì sẽ có người sửa giúp sau.",
            },
            correct_option="B",
            explanation="Ưu tiên làm rõ điểm khác biệt cốt lõi trước khi áp dụng.",
            intent="repair",
        )

    if teaching_strategy == "give_example":
        return CheckQuestion(
            question=f"Cách nào kiểm tra hiểu «{topic}» tốt nhất?",
            options={
                "A": "Chỉ đọc lại định nghĩa rồi chuyển bài.",
                "B": "Áp dụng vào một ví dụ ngắn và giải thích vì sao.",
                "C": "Nhớ nguyên văn câu trong slide.",
                "D": "Hỏi lại đúng câu định nghĩa nhiều lần.",
            },
            correct_option="B",
            explanation="Áp dụng vào ví dụ là bằng chứng hiểu tốt hơn nhớ máy móc.",
            intent="example",
        )

    if teaching_strategy in {"validate_understanding", "give_hint"} or understanding_score < 90:
        return CheckQuestion(
            question=f"Đâu là dấu hiệu bạn ĐÃ hiểu «{topic}»?",
            options={
                "A": "Tự diễn đạt lại ý chính bằng lời của mình.",
                "B": "Chỉ xin tóm tắt slide mà chưa nói gì thêm.",
                "C": "Gõ 'ok' sau câu trả lời của tutor.",
                "D": "Nhờ tutor làm hộ bài tập liên quan.",
            },
            correct_option="A",
            explanation="Diễn đạt lại bằng lời mình là bằng chứng hiểu.",
            intent="check",
        )

    return CheckQuestion(
        question=f"Sau khi nắm «{topic}», bước tiếp theo hợp lý là gì?",
        options={
            "A": "Dừng hẳn, không cần kiểm tra lại.",
            "B": "Sang khái niệm liên quan và tự kiểm bằng một ví dụ ngắn.",
            "C": "Hỏi lại đúng câu định nghĩa vừa học.",
            "D": "Bỏ qua mọi phần còn lại của buổi học.",
        },
        correct_option="B",
        explanation="Khi đã hiểu tốt, nên chuyển chủ đề liên quan kèm kiểm tra nhẹ.",
        intent="advance",
    )


def generate_followup(
    ctx: ConversationContext,
    teaching_strategy: str,
    misconceptions: list[str],
    understanding_score: int,
    understanding_reason: str = "",
    confidence: str = "medium",
) -> tuple[list[str], str, CheckQuestion]:
    """Return ([prompt_text], provider, CheckQuestion).

    `follow_ups[0]` là đề MCQ hiển thị cho HV (không lộ đáp án).
    """
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
            mcq = _normalize_mcq(data if isinstance(data, dict) else {})
            if mcq:
                return [mcq.prompt_text()], provider, mcq
        except Exception:
            pass

    mcq = _template_check_question(
        ctx, teaching_strategy, misconceptions, understanding_score
    )
    return [mcq.prompt_text()], "template", mcq


# Backward-compatible alias for eval/flow_lab
def _template_followup(
    ctx: ConversationContext,
    teaching_strategy: str,
    misconceptions: list[str],
    understanding_score: int,
) -> str:
    return _template_check_question(
        ctx, teaching_strategy, misconceptions, understanding_score
    ).stem_for_eval()


# Re-export for older imports
from .grading import grade_check_answer  # noqa: E402,F401
