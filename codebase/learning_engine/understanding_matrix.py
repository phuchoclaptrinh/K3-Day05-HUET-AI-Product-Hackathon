"""Understanding Matrix — rubric đo mức hiểu có gắn ngữ cảnh slide/transcript.

Không thay thế LLM-as-Judge; cung cấp baseline tín hiệu kiểm chứng được
(đặc biệt khi có LESSON_EXCERPT từ PDF/transcript) để:
- Prompt estimator chấm đúng hơn
- Hard-rule (dán slide → không tính là hiểu)
- UI hiện ma trận 4 trục cạnh % tổng
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from .context import ConversationContext
from .lesson_retriever import _tokens

Band = Literal["low", "mid", "high"]

# Trọng số hợp thành % tổng (khi dùng baseline / sau khi có misconception)
W_EVIDENCE = 0.55
W_GROUNDING = 0.15
W_AUTHENTICITY = 0.15
W_ACCURACY = 0.15


@dataclass
class UnderstandingMatrix:
    """4 trục 0–100 + band bằng chứng."""

    evidence: int = 40
    lesson_grounding: int = 0
    authenticity: int = 100
    concept_accuracy: int = 100
    evidence_band: Band = "mid"
    paste_detected: bool = False
    has_lesson_context: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def composite_baseline(self) -> int:
        """Điểm hợp thành từ matrix (baseline heuristic)."""
        if self.paste_detected or self.authenticity <= 45:
            return min(35, max(10, int(0.4 * self.evidence + 0.6 * self.authenticity)))
        if self.concept_accuracy < 50:
            return min(35, max(8, int(0.35 * self.evidence + 0.65 * self.concept_accuracy)))
        raw = (
            W_EVIDENCE * self.evidence
            + W_GROUNDING * self.lesson_grounding
            + W_AUTHENTICITY * self.authenticity
            + W_ACCURACY * self.concept_accuracy
        )
        # Hỏi đúng bài nhưng chưa tự diễn đạt → không đẩy lên mid/high chỉ vì grounding
        if self.evidence < 40 and self.lesson_grounding >= 50:
            raw = min(raw, 38)
        return max(0, min(100, int(round(raw))))


def band_of_score(score: int) -> Band:
    if score < 40:
        return "low"
    if score <= 70:
        return "mid"
    return "high"


def _clamp(n: int) -> int:
    return max(0, min(100, int(n)))


def _lesson_grounding_score(student: str, excerpt: str, headings: list[str]) -> int:
    """Mức tin nhắn bám khái niệm trong slide (không phải tỷ lệ dán nguyên văn)."""
    if not excerpt.strip():
        return 0
    s_tok = _tokens(student)
    e_tok = _tokens(excerpt)
    if not s_tok or not e_tok:
        return 0
    inter = s_tok & e_tok
    # Coverage của token học viên trên excerpt — thấp khi hỏi lạc đề
    coverage = len(inter) / max(1, len(s_tok))
    # Hit heading = tín hiệu mạnh đang đúng mục slide
    h_tok = _tokens(" ".join(headings or []))
    head_hit = bool(s_tok & h_tok)
    # Điểm: coverage vừa phải tốt; coverage quá cao (≥0.55) thường là dán — chấm grounding riêng
    if coverage >= 0.55 and len(s_tok) >= 8:
        base = 55  # vẫn "đúng bài" nhưng authenticity sẽ hạ
    else:
        base = int(100 * min(1.0, coverage / 0.35))
    if head_hit:
        base = min(100, base + 18)
    # Ít nhất 2 thuật ngữ dài (≥6) trùng excerpt
    long_hits = sum(1 for t in inter if len(t) >= 6)
    if long_hits >= 2:
        base = min(100, base + 12)
    elif long_hits == 0 and coverage < 0.12:
        base = min(base, 20)
    return _clamp(base)


def _evidence_from_text(text: str) -> tuple[int, list[str]]:
    """Heuristic bằng chứng tự hiểu (không dùng LLM)."""
    notes: list[str] = []
    t = text.lower()
    short = len(t.strip()) < 12 or t.strip() in {"hi", "ok", "hả", "asds", "hello"}
    out_of_scope = bool(re.search(r"làm giúp|viết giúp|làm hộ|đáp án quiz|cho điểm|base64", t))
    summarize = bool(re.search(r"tóm tắt|tom tat|tóm gọn|summary", t))
    what_is = bool(re.search(r"là gì\b|la gi\b", t)) and len(t) < 120
    explain = bool(re.search(r"giải thích|explain|tại sao|như thế nào|khác gì|khác nhau", t))
    self_explain = bool(
        re.search(
            r"theo em|theo mình|tôi hiểu|em hiểu|em đang hình dung|em nhớ|đúng vậy|đúng không|"
            r"em nghĩ|mình hiểu|theo cách hiểu",
            t,
        )
    )
    compare = bool(re.search(r"khác nhau|so với|so sánh|versus|vs\b", t)) and len(t) > 60

    if short:
        notes.append("Tin nhắn quá ngắn — chưa lộ bằng chứng hiểu.")
        return 15, notes
    if out_of_scope:
        notes.append("Yêu cầu ngoài học tập — không tính bằng chứng hiểu bài.")
        return 18, notes
    if self_explain or compare:
        notes.append("Có dấu hiệu tự diễn đạt / kiểm chứng bằng lời mình.")
        return 78, notes
    if summarize:
        notes.append("Xin tóm tắt — chưa chứng minh đã hiểu.")
        return 30, notes
    if what_is:
        notes.append("Hỏi định nghĩa — bằng chứng hiểu còn thấp.")
        return 36, notes
    if explain:
        notes.append("Đang tìm hiểu khái niệm — bằng chứng một phần / thấp.")
        return 42, notes
    notes.append("Có câu hỏi học tập nhưng chưa đủ tín hiệu tự hiểu.")
    return 40, notes


def _detect_wrong_claims(text: str) -> list[str]:
    misconceptions: list[str] = []
    t = text.lower()
    if re.search(r"stack\s*(là|=)\s*queue|queue\s*(là|=)\s*stack|nhầm.*stack.*queue", t):
        misconceptions.append("Nhầm Stack với Queue")
    if re.search(r"binary search.*(o\(n\)|tuyến tính)|độ phức tạp.*binary.*o\(n\)", t):
        misconceptions.append("Sai Big-O của Binary Search (cho là O(n))")
    if re.search(
        r"google\s*search|llm.*=.*google|llm.*(chỉ\s*là|là)\s*.*search|máy tìm kiếm",
        t,
    ):
        misconceptions.append("Hiểu sai bản chất LLM (coi như máy tìm kiếm)")
    return misconceptions


def compute_understanding_matrix(
    ctx: ConversationContext,
    misconceptions: list[str] | None = None,
) -> UnderstandingMatrix:
    """Tính matrix baseline từ hội thoại + LESSON_EXCERPT."""
    lesson = ctx.lesson
    excerpt = (lesson.excerpt or "").strip()
    has_lesson = bool(excerpt)
    overlap = float(lesson.overlap_ratio or 0.0)
    paste = overlap >= 0.55 and len(_tokens(ctx.student_latest)) >= 8

    evidence, notes = _evidence_from_text(ctx.student_latest)
    grounding = _lesson_grounding_score(
        ctx.student_latest, excerpt, list(lesson.headings or [])
    )
    authenticity = _clamp(int(round(100 * (1.0 - overlap))))
    if paste:
        authenticity = min(authenticity, 35)
        evidence = min(evidence, 32)
        notes = [
            "Trùng cao với excerpt slide/transcript — giống dán lại, không phải tự hiểu."
        ] + [n for n in notes if "dán" not in n.lower()]

    misc = list(misconceptions) if misconceptions is not None else _detect_wrong_claims(
        ctx.student_latest
    )
    if misc:
        # Accuracy thấp; giữ evidence để UI phân biệt "có diễn đạt nhưng sai" vs "chưa có bằng chứng"
        accuracy = 28
        notes.append("Phát hiện khẳng định sai khái niệm so với tín hiệu hội thoại/bài.")
    else:
        accuracy = 100

    if has_lesson:
        if grounding >= 55 and not paste:
            notes.append(
                f"Bám ngữ cảnh buổi «{lesson.session_label or lesson.session_id}» "
                f"(grounding {grounding}%)."
            )
        elif grounding < 25 and not paste:
            notes.append(
                "Câu hỏi ít trùng khái niệm trong excerpt đã retrieve — "
                "độ tin cậy chấm theo slide thấp hơn."
            )
    else:
        notes.append("Chưa có excerpt bài học — chấm chủ yếu theo tín hiệu hội thoại.")

    matrix = UnderstandingMatrix(
        evidence=_clamp(evidence),
        lesson_grounding=_clamp(grounding),
        authenticity=_clamp(authenticity),
        concept_accuracy=_clamp(accuracy),
        evidence_band=band_of_score(evidence),
        paste_detected=paste,
        has_lesson_context=has_lesson,
        notes=notes[:5],
    )
    matrix.evidence_band = band_of_score(matrix.evidence)
    return matrix


def apply_matrix_guards(score: int, matrix: UnderstandingMatrix) -> int:
    """Hard-rule sau LLM: dán slide / accuracy thấp → trần điểm."""
    s = _clamp(score)
    if matrix.paste_detected or matrix.authenticity <= 45:
        s = min(s, 35)
    if matrix.concept_accuracy < 50:
        s = min(s, 38)
    # Có excerpt nhưng lạc đề hoàn toàn: không cho high chỉ vì model “thấy câu hay”
    if matrix.has_lesson_context and matrix.lesson_grounding < 18 and not matrix.paste_detected:
        if s >= 71:
            s = min(s, 68)
    return s


def matrix_prompt_block(matrix: UnderstandingMatrix) -> str:
    return (
        "UNDERSTANDING_MATRIX (baseline tín hiệu, 0–100):\n"
        f"- evidence (bằng chứng tự hiểu): {matrix.evidence} → band {matrix.evidence_band}\n"
        f"- lesson_grounding (bám slide/transcript): {matrix.lesson_grounding}\n"
        f"- authenticity (không dán nguyên văn): {matrix.authenticity}"
        f"{' · PASTE_DETECTED' if matrix.paste_detected else ''}\n"
        f"- concept_accuracy (không khẳng định sai): {matrix.concept_accuracy}\n"
        f"- has_lesson_context: {matrix.has_lesson_context}\n"
        f"- notes: {matrix.notes or ['—']}\n"
        "Dùng matrix để neo điểm: PASTE → 0–39; hỏi định nghĩa đúng bài vẫn có thể low evidence; "
        "chỉ tăng mid/high khi học viên TỰ DIỄN ĐẠT khớp khái niệm trong EXCERPT."
    )
