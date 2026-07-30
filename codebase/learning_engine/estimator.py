from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from .context import ConversationContext
from .llm_client import call_llm_json, resolve_mode

Confidence = Literal["low", "medium", "high"]

SYSTEM_PROMPT = """Bạn là giám khảo sư phạm cho AI Tutor trong lớp học (VLearn).
Nhiệm vụ: ước lượng MỨC HIỂU của học viên và phát hiện misconception (nếu có).
KHÔNG chấm chất lượng câu trả lời của tutor.
KHÔNG bịa bằng chứng không có trong hội thoại.

Trả về JSON đúng schema:
{
  "understanding_score": <int 0-100>,
  "understanding_reason": "<≤2 câu tiếng Việt>",
  "confidence": "low|medium|high",
  "misconceptions": ["<hiểu lầm cụ thể>", ...]
}

## Cách cho điểm — chấm theo BẰNG CHỨNG HIỂU, không theo độ khó câu hỏi
- 0-39: học viên CHƯA có bằng chứng hiểu. Gồm: xin tóm tắt, xin giải thích, hỏi định nghĩa,
  DÁN LẠI nguyên văn đoạn slide rồi nhờ giải thích, greeting, tin nhắn vô nghĩa,
  yêu cầu ngoài phạm vi học tập, hoặc phát biểu sai kiến thức.
- 40-70: bằng chứng MỘT PHẦN. Học viên mô tả tình huống cụ thể của mình, dùng đúng một phần
  thuật ngữ, hoặc nêu hiểu biết còn thiếu.
- 71-100: học viên CHỨNG MINH được hiểu: diễn đạt lại khái niệm bằng lời của mình,
  so sánh có nội dung, hoặc kiểm chứng lại một phát biểu đúng.

Quan trọng: câu hỏi càng khó KHÔNG làm điểm cao hơn. Dán một đoạn slide phức tạp và nói
"giải thích giúp em" vẫn thuộc 0-39, vì học viên chưa đóng góp bằng chứng hiểu nào.

## Quy tắc misconceptions — mặc định là [] 
CHỈ ghi misconception khi học viên KHẲNG ĐỊNH một điều sai (câu khẳng định, hoặc câu hỏi
đuôi kiểu "... đúng không?" kèm nội dung sai). Tối đa 3 item, mỗi item ngắn và cụ thể.

TUYỆT ĐỐI KHÔNG ghi misconception trong các trường hợp sau:
- Học viên chỉ ĐẶT CÂU HỎI MỞ ("... là gì", "... do đâu", "tại sao ...", "... khác gì nhau",
  "có mấy loại ..."). Hỏi không phải là hiểu sai.
- Học viên chưa biết / chưa nhắc tới một kiến thức. Thiếu kiến thức KHÔNG phải misconception.
- Học viên dùng phép ẩn dụ hoặc cách hình dung mà về cơ bản ĐÚNG, dù chưa chính xác tuyệt đối.
- Tin nhắn quá ngắn, greeting, vô nghĩa, hoặc yêu cầu ngoài phạm vi.
- Không viết misconception kiểu chung chung như "chưa hiểu bài", "thiếu kiến thức nền".

Tự kiểm trước khi trả về: trích được CHÍNH XÁC câu nào của học viên chứa phát biểu sai?
Nếu không trích được → misconceptions phải là [].
"""


@dataclass
class EstimateResult:
    understanding_score: int
    understanding_reason: str
    confidence: Confidence
    misconceptions: list[str] = field(default_factory=list)
    provider: str = "mock"
    raw: dict | None = None


def _clamp_score(value: object) -> int:
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        n = 40
    return max(0, min(100, n))


def _norm_confidence(value: object) -> Confidence:
    v = str(value or "medium").strip().lower()
    if v in {"low", "medium", "high"}:
        return v  # type: ignore[return-value]
    return "medium"


def _norm_misconceptions(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value[:3]:
        s = str(item).strip()
        if s and s.lower() not in {"chưa hiểu bài", "chua hieu bai", "không hiểu", "khong hieu"}:
            out.append(s)
    return out


def estimate_understanding(ctx: ConversationContext) -> EstimateResult:
    mode = resolve_mode()
    if mode == "mock":
        return _mock_estimate(ctx)

    user = f"""TOPIC_HINT: {ctx.topic_hint or "(không có)"}
DAY_CODE: {ctx.day_code or "(không có)"}

HISTORY:
{ctx.history_text() or "(trống — turn đầu)"}

STUDENT_LATEST:
{ctx.student_latest}
"""
    try:
        data, provider = call_llm_json(SYSTEM_PROMPT, user)
        return EstimateResult(
            understanding_score=_clamp_score(data.get("understanding_score")),
            understanding_reason=str(data.get("understanding_reason") or "").strip()
            or "Không có lý do từ model.",
            confidence=_norm_confidence(data.get("confidence")),
            misconceptions=_norm_misconceptions(data.get("misconceptions")),
            provider=provider,
            raw=data,
        )
    except Exception as exc:  # noqa: BLE001 — fallback for demo resilience
        mock = _mock_estimate(ctx)
        mock.understanding_reason = f"[fallback mock sau lỗi LLM: {exc}] {mock.understanding_reason}"
        mock.provider = "mock_fallback"
        return mock


def _mock_estimate(ctx: ConversationContext) -> EstimateResult:
    """Heuristic judge — chỉ dùng khi không có API key / fallback."""
    text = ctx.student_latest.lower()
    misconceptions: list[str] = []

    # Explicit wrong claims (synthetic patterns)
    if re.search(r"stack\s*(là|=)\s*queue|queue\s*(là|=)\s*stack|nhầm.*stack.*queue", text):
        misconceptions.append("Nhầm Stack với Queue")
    if re.search(r"binary search.*(o\(n\)|tuyến tính)|độ phức tạp.*binary.*o\(n\)", text):
        misconceptions.append("Sai Big-O của Binary Search (cho là O(n))")
    if re.search(
        r"google\s*search|llm.*=.*google|llm.*(chỉ\s*là|là)\s*.*search|máy tìm kiếm",
        text,
    ):
        misconceptions.append("Hiểu sai bản chất LLM (coi như máy tìm kiếm)")

    # Low-signal requests
    summarize = bool(re.search(r"tóm tắt|tom tat|tóm gọn|summary", text))
    what_is = bool(re.search(r"là gì\b|la gi\b", text)) and len(text) < 120
    short = len(text.strip()) < 12 or text.strip() in {"hi", "ok", "hả", "asds", "hello"}
    out_of_scope = bool(re.search(r"làm giúp|viết giúp|làm hộ|đáp án quiz|cho điểm|base64", text))
    self_explain = bool(
        re.search(
            r"theo em|theo mình|tôi hiểu|em hiểu|em đang hình dung|em nhớ|đúng vậy|đúng không",
            text,
        )
    )

    if misconceptions:
        return EstimateResult(
            understanding_score=28,
            understanding_reason="Học viên lộ tín hiệu hiểu sai khái niệm trong câu hỏi.",
            confidence="high",
            misconceptions=misconceptions,
            provider="mock",
        )

    if short:
        return EstimateResult(
            understanding_score=15,
            understanding_reason="Tin nhắn quá ngắn / chưa lộ mức hiểu về nội dung bài.",
            confidence="low",
            misconceptions=[],
            provider="mock",
        )

    if out_of_scope:
        return EstimateResult(
            understanding_score=20,
            understanding_reason="Yêu cầu ngoài phạm vi học tập; chưa thể hiện hiểu bài.",
            confidence="low",
            misconceptions=[],
            provider="mock",
        )

    # Explains / compares / applies → higher (trước what_is / summarize)
    if self_explain:
        return EstimateResult(
            understanding_score=78,
            understanding_reason="Học viên đang diễn đạt / kiểm chứng bằng lời mình — tín hiệu hiểu khá tốt.",
            confidence="medium",
            misconceptions=[],
            provider="mock",
        )

    if summarize:
        return EstimateResult(
            understanding_score=32,
            understanding_reason="Chỉ yêu cầu tóm tắt/slide — chưa chứng minh đã hiểu bằng lời mình.",
            confidence="low",
            misconceptions=[],
            provider="mock",
        )

    if what_is:
        return EstimateResult(
            understanding_score=38,
            understanding_reason="Đang hỏi định nghĩa lần đầu; chưa có bằng chứng hiểu sâu.",
            confidence="low",
            misconceptions=[],
            provider="mock",
        )

    if re.search(r"giải thích|explain|tại sao|như thế nào|khác gì|khác nhau", text):
        return EstimateResult(
            understanding_score=45,
            understanding_reason="Đang tìm hiểu khái niệm; mức hiểu trung bình-thấp trước khi được kiểm tra.",
            confidence="medium",
            misconceptions=[],
            provider="mock",
        )

    return EstimateResult(
        understanding_score=42,
        understanding_reason="Có câu hỏi học tập nhưng chưa đủ tín hiệu để kết luận hiểu sâu.",
        confidence="medium",
        misconceptions=[],
        provider="mock",
    )
