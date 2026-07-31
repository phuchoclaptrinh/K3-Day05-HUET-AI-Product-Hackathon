from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from .context import ConversationContext
from .llm_client import call_llm_json, resolve_mode
from .understanding_matrix import (
    UnderstandingMatrix,
    apply_matrix_guards,
    compute_understanding_matrix,
    matrix_prompt_block,
)

Confidence = Literal["low", "medium", "high"]

SYSTEM_PROMPT = """Bạn là giám khảo sư phạm cho AI Tutor trong lớp học (VLearn).
Nhiệm vụ: ước lượng MỨC HIỂU của học viên và phát hiện misconception (nếu có).
KHÔNG chấm chất lượng câu trả lời của tutor.
KHÔNG bịa bằng chứng không có trong hội thoại.

Bạn ĐƯỢC CUNG CẤP:
1) LESSON_EXCERPT — nội dung slide/transcript buổi học đã retrieve
2) UNDERSTANDING_MATRIX — baseline 4 trục đã tính từ tin nhắn + excerpt

## Ma trận 4 trục (phải neo điểm theo đây)
- evidence: học viên có CHỨNG MINH được mình hiểu bằng lời mình không?
- lesson_grounding: tin nhắn có bám khái niệm trong LESSON_EXCERPT không?
- authenticity: có phải DÁN LẠI slide/excerpt không? (PASTE_DETECTED → luôn low)
- concept_accuracy: có KHẲNG ĐỊNH sai so với đúng ý trong excerpt không?

understanding_score hợp thành chủ yếu từ evidence; các trục còn lại dùng để
trần điểm / hạ confidence — KHÔNG tăng điểm chỉ vì câu hỏi “khó” hoặc đúng bài.

Trả về JSON đúng schema:
{
  "understanding_score": <int 0-100>,
  "understanding_reason": "<≤2 câu tiếng Việt; nêu rõ liên hệ với slide nếu có>",
  "confidence": "low|medium|high",
  "misconceptions": ["<hiểu lầm cụ thể>", ...],
  "matrix_comment": "<≤1 câu: trục nào quyết định điểm lần này>"
}

## Band bằng chứng (evidence) — KHÔNG theo độ khó câu hỏi
- 0-39: chưa có bằng chứng hiểu. Xin tóm tắt / hỏi định nghĩa / dán slide /
  greeting / ngoài phạm vi / phát biểu sai.
- 40-70: bằng chứng một phần — mô tả tình huống, dùng đúng một phần thuật ngữ bài.
- 71-100: tự diễn đạt khái niệm trong excerpt bằng lời mình, so sánh có nội dung,
  hoặc kiểm chứng phát biểu đúng với bài.

Quan trọng:
- PASTE_DETECTED hoặc authenticity thấp → score 0-39, confidence=low, misconceptions=[]
- Hỏi đúng khái niệm trong slide nhưng chỉ “là gì / giải thích giúp” → vẫn 0-39
- Có LESSON_EXCERPT mà tin nhắn lạc đề (grounding rất thấp) → confidence=low;
  không cho high chỉ vì câu nghe “hay”

## Quy tắc misconceptions — mặc định []
CHỈ ghi khi học viên KHẲNG ĐỊNH điều sai (hoặc "... đúng không?" kèm nội dung sai).
Ưu tiên đối chiếu với đúng ý trong LESSON_EXCERPT. Tối đa 3 item, cụ thể.

TUYỆT ĐỐI KHÔNG ghi misconception khi:
- Chỉ đặt câu hỏi mở ("là gì", "tại sao", "khác gì")
- Thiếu kiến thức / chưa nhắc tới
- Ẩn dụ về cơ bản đúng
- Greeting / ngắn / ngoài phạm vi
- Không trích được đúng câu chứa phát biểu sai → misconceptions = []
"""


@dataclass
class EstimateResult:
    understanding_score: int
    understanding_reason: str
    confidence: Confidence
    misconceptions: list[str] = field(default_factory=list)
    provider: str = "mock"
    raw: dict | None = None
    matrix: UnderstandingMatrix | None = None
    matrix_comment: str = ""

    def matrix_dict(self) -> dict[str, Any]:
        if self.matrix is None:
            return {}
        return self.matrix.to_dict()


def _clamp_score(value: object) -> int:
    try:
        n = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        n = 40
    return max(0, min(100, n))


def _norm_confidence(value: object) -> Confidence:
    v = str(value or "medium").strip().lower()
    if v in {"low", "medium", "high"}:
        return v  # type: ignore[return-type]
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


def _adjust_confidence(conf: Confidence, matrix: UnderstandingMatrix) -> Confidence:
    if matrix.paste_detected:
        return "low"
    if matrix.has_lesson_context and matrix.lesson_grounding < 22:
        if conf == "high":
            return "medium"
        if conf == "medium":
            return "low"
    return conf


def estimate_understanding(ctx: ConversationContext) -> EstimateResult:
    mode = resolve_mode()
    if mode == "mock":
        return _mock_estimate(ctx)

    pre_matrix = compute_understanding_matrix(ctx)
    user = f"""TOPIC_HINT: {ctx.topic_hint or "(không có)"}
DAY_CODE / SESSION: {ctx.session_id or ctx.day_code or "(không có)"}
OVERLAP_WITH_LESSON: {ctx.lesson.overlap_ratio}

{matrix_prompt_block(pre_matrix)}

LESSON_CONTEXT (slide/transcript excerpt):
{ctx.lesson_prompt()}

HISTORY:
{ctx.history_text() or "(trống — turn đầu)"}

STUDENT_LATEST:
{ctx.student_latest}
"""
    try:
        data, provider = call_llm_json(SYSTEM_PROMPT, user)
        misc = _norm_misconceptions(data.get("misconceptions"))
        matrix = compute_understanding_matrix(ctx, misconceptions=misc)
        score = apply_matrix_guards(_clamp_score(data.get("understanding_score")), matrix)
        reason = str(data.get("understanding_reason") or "").strip() or "Không có lý do từ model."
        if matrix.paste_detected and "dán" not in reason.lower() and "trùng" not in reason.lower():
            reason = (
                "Tin nhắn trùng cao với excerpt slide — chưa phải bằng chứng tự hiểu. " + reason
            )[:280]
        comment = str(data.get("matrix_comment") or "").strip()
        if not comment and matrix.notes:
            comment = matrix.notes[0]
        return EstimateResult(
            understanding_score=score,
            understanding_reason=reason,
            confidence=_adjust_confidence(_norm_confidence(data.get("confidence")), matrix),
            misconceptions=[] if matrix.paste_detected else misc,
            provider=provider,
            raw=data,
            matrix=matrix,
            matrix_comment=comment,
        )
    except Exception as exc:  # noqa: BLE001 — fallback for demo resilience
        mock = _mock_estimate(ctx)
        mock.understanding_reason = f"[fallback mock sau lỗi LLM: {exc}] {mock.understanding_reason}"
        mock.provider = "mock_fallback"
        return mock


def _mock_estimate(ctx: ConversationContext) -> EstimateResult:
    """Heuristic judge — chỉ dùng khi không có API key / fallback."""
    pre = compute_understanding_matrix(ctx)
    misc = [] if pre.paste_detected else [
        m
        for m in (
            "Nhầm Stack với Queue"
            if re.search(
                r"stack\s*(là|=)\s*queue|queue\s*(là|=)\s*stack|nhầm.*stack.*queue",
                ctx.student_latest.lower(),
            )
            else None,
            "Sai Big-O của Binary Search (cho là O(n))"
            if re.search(
                r"binary search.*(o\(n\)|tuyến tính)|độ phức tạp.*binary.*o\(n\)",
                ctx.student_latest.lower(),
            )
            else None,
            "Hiểu sai bản chất LLM (coi như máy tìm kiếm)"
            if re.search(
                r"google\s*search|llm.*=.*google|llm.*(chỉ\s*là|là)\s*.*search|máy tìm kiếm",
                ctx.student_latest.lower(),
            )
            else None,
        )
        if m
    ]
    matrix = compute_understanding_matrix(ctx, misconceptions=misc)
    score = matrix.composite_baseline()
    conf: Confidence = "low" if (matrix.paste_detected or score < 40) else (
        "high" if misc or score >= 75 else "medium"
    )
    conf = _adjust_confidence(conf, matrix)
    reason = (matrix.notes[0] if matrix.notes else "Ước lượng theo matrix baseline.")
    if matrix.has_lesson_context and matrix.lesson_grounding >= 40 and not matrix.paste_detected:
        reason = f"{reason} (bám slide/transcript: {matrix.lesson_grounding}%)."
    return EstimateResult(
        understanding_score=score,
        understanding_reason=reason[:280],
        confidence=conf,
        misconceptions=misc,
        provider="mock",
        matrix=matrix,
        matrix_comment=matrix.notes[0] if matrix.notes else "",
    )
