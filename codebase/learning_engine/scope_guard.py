"""Scope Guard 3 mức — dựa trên transcript VLearn.

1) in_lesson — khớp bài giảng (transcript) → trả lời bình thường
2) related_external — hơi liên quan AI/product nhưng ngoài bài → vẫn trả lời + take-note
3) refuse — linh tinh / làm hộ / chào hỏi → từ chối, không gọi API
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .transcript_index import is_related_domain, score_against_transcript

LEARNING_INTENT_PATTERNS = [
    r"\blà gì\b",
    r"\bla gi\b",
    r"\bnghĩa là\b",
    r"\bgiải thích\b",
    r"\bgiai thich\b",
    r"\btóm tắt\b",
    r"\btom tat\b",
    r"\btóm gọn\b",
    r"\bphân biệt\b",
    r"\bso sánh\b",
    r"\bkhác (gì|nhau)\b",
    r"\bví dụ\b",
    r"\bvi du\b",
    r"\bđịnh nghĩa\b",
    r"\bcách (hoạt động|làm|dùng)\b",
    r"\bcơ chế\b",
    r"\btrang\s*\d+",
    r"\bslide\b",
    r"\bbài học\b",
    r"\bbai hoc\b",
    r"\bwhat is\b",
    r"\bexplain\b",
    r"\bdifference\b",
    r"\bhow does\b",
    r"\btại sao\b",
    r"\btai sao\b",
    r"\bthế nào\b",
    r"\bthe nao\b",
    r"\bnhư thế nào\b",
    r"\bhoạt động\b",
]

OUT_OF_SCOPE_PATTERNS = [
    r"base64",
    r"làm\s*h[ộo]\b",
    r"lam\s*ho\b",
    r"vi[ệe]t\s*gi[úu]p\b",
    r"đáp\s*án\s*quiz",
    r"cho\s*điểm",
    r"hack\s*(facebook|instagram|zalo)",
    r"mã\s*độc|malware|ransomware",
    r"cá\s*độ|cờ\s*bạc",
    r"thời\s*tiết\s*hôm\s*nay",
    r"giá\s*bitcoin|chứng\s*khoán\s*hôm\s*nay",
    r"nấu\s*ăn|công\s*thức\s*nấu|nấu\s*phở",
    r"bóng\s*đá\s*hôm\s*nay|tỷ\s*số",
    r"tán\s*tỉnh|hẹn\s*hò",
    r"viết\s*code\s*nộp\s*bài",
    r"dịch\s*giúp\s*toàn\s*bộ",
]

GREETING_PATTERNS = [
    r"^(hi|hello|hey|chào|xin chào|hola)[\s!.]*$",
    r"^(ok|oke|thanks|cảm ơn|cam on)[\s!.]*$",
]

# Ngưỡng khớp transcript
IN_LESSON_SCORE = 28

TAKE_NOTE_EXTERNAL = (
    "📝 **Take-note:** Phần này là kiến thức **bên ngoài / ít gắn trực tiếp** với nội dung "
    "đã giảng trên transcript buổi học. Mình vẫn giải thích để bạn nối mạch, "
    "nhưng hãy đối chiếu lại slide / bài giảng chính của khoá."
)


@dataclass
class ScopeDecision:
    """in_scope=True ⇒ được phép gọi API (in_lesson hoặc related_external)."""

    in_scope: bool
    reason: str
    matched_terms: list[str]
    category: str  # in_lesson | related_external | refuse | greeting | ambiguous
    refusal_message: str = ""
    take_note: str = ""
    transcript_score: int = 0
    heading_hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _has_learning_intent(msg: str) -> bool:
    return any(re.search(pat, msg, flags=re.IGNORECASE) for pat in LEARNING_INTENT_PATTERNS)


def check_scope(student_message: str, topic_hint: str = "", day_code: str = "") -> ScopeDecision:
    """Quyết định 3 mức phạm vi — local, không gọi API."""
    msg = (student_message or "").strip()
    msg_l = msg.lower()
    hint = (topic_hint or "").strip()

    if len(msg) < 2:
        return ScopeDecision(
            in_scope=False,
            reason="Tin nhắn quá ngắn / trống.",
            matched_terms=[],
            category="ambiguous",
            refusal_message=(
                "Mình chưa rõ bạn muốn hỏi phần nào trong buổi học. "
                "Hãy hỏi một khái niệm trên slide / transcript "
                "(ví dụ: Transformer, RAG, Double Diamond, Problem Statement)."
            ),
        )

    for pat in GREETING_PATTERNS:
        if re.search(pat, msg_l, flags=re.IGNORECASE):
            return ScopeDecision(
                in_scope=False,
                reason="Chào hỏi / tin xã giao — không gọi API dạy bài.",
                matched_terms=[],
                category="greeting",
                refusal_message=(
                    "Chào bạn! Mình hỗ trợ kiến thức bám **transcript / slide** khoá AI Thực Chiến. "
                    "Bạn muốn hỏi khái niệm nào trong buổi học "
                    "(LLM, Transformer, RAG, Agent, Problem Statement...)?"
                ),
            )

    for pat in OUT_OF_SCOPE_PATTERNS:
        if re.search(pat, msg_l, flags=re.IGNORECASE):
            return ScopeDecision(
                in_scope=False,
                reason=f"Câu hỏi linh tinh / ngoài thẩm quyền: {pat}",
                matched_terms=[],
                category="refuse",
                refusal_message=(
                    "Yêu cầu này nằm ngoài phạm vi trợ giảng học tập "
                    "(không làm hộ bài, không trả lời chủ đề linh tinh ngoài khoá). "
                    "Hãy hỏi lại một khái niệm trong buổi học trên transcript/slide."
                ),
            )

    scored = score_against_transcript(msg, hint, day_code)
    hits = list(scored.get("hits") or [])
    heading_hits = list(scored.get("heading_hits") or [])
    t_score = int(scored.get("score") or 0)
    learning = _has_learning_intent(msg_l)
    related = is_related_domain(f"{msg} {hint}")

    # --- 1) Trong bài (transcript) ---
    if t_score >= IN_LESSON_SCORE or heading_hits or (hint and t_score >= 15 and hits):
        matched = heading_hits[:3] + hits[:5]
        return ScopeDecision(
            in_scope=True,
            reason="Khớp chủ đề trên transcript / ngữ cảnh bài học.",
            matched_terms=matched[:8],
            category="in_lesson",
            transcript_score=t_score,
            heading_hits=heading_hits,
        )

    # topic_hint rõ ràng → ưu tiên coi là đang học trong lớp
    if len(hint) >= 3 and (learning or hits or related):
        return ScopeDecision(
            in_scope=True,
            reason="Có ngữ cảnh bài học (topic_hint) — coi là trong buổi.",
            matched_terms=[f"topic_hint:{hint[:40]}"] + hits[:4],
            category="in_lesson",
            transcript_score=max(t_score, 20),
            heading_hits=heading_hits,
        )

    # --- 2) Hơi liên quan, ngoài bài → vẫn trả lời + take-note ---
    if learning and (related or t_score > 0 or hits):
        return ScopeDecision(
            in_scope=True,
            reason="Câu hỏi học thuật hơi liên quan nhưng khớp transcript yếu — trả lời kèm take-note.",
            matched_terms=hits[:6] or (["related_domain"] if related else ["learning_intent"]),
            category="related_external",
            take_note=TAKE_NOTE_EXTERNAL,
            transcript_score=t_score,
            heading_hits=heading_hits,
        )

    if related and learning:
        return ScopeDecision(
            in_scope=True,
            reason="Chủ đề AI/tech gần khoá nhưng ngoài transcript — trả lời kèm take-note.",
            matched_terms=["related_domain"],
            category="related_external",
            take_note=TAKE_NOTE_EXTERNAL,
            transcript_score=t_score,
            heading_hits=heading_hits,
        )

    # Câu hỏi domain gần khoá (có dấu ? hoặc đủ dài) dù không khớp mẫu "là gì"
    if related and ( "?" in msg or len(msg.split()) >= 3):
        return ScopeDecision(
            in_scope=True,
            reason="Chủ đề AI/tech gần khoá — trả lời kèm take-note.",
            matched_terms=["related_domain"],
            category="related_external",
            take_note=TAKE_NOTE_EXTERNAL,
            transcript_score=t_score,
            heading_hits=heading_hits,
        )

    if learning and t_score == 0 and not related:
        # "là gì" linh tinh không thuộc AI/product → từ chối
        return ScopeDecision(
            in_scope=False,
            reason="Có hình thức hỏi học nhưng không liên quan transcript / domain khoá.",
            matched_terms=[],
            category="refuse",
            refusal_message=(
                "Câu hỏi mang tính học thuật nhưng **không liên quan** nội dung khoá "
                "(transcript AI Thực Chiến / VLearn). "
                "Mình chỉ hỗ trợ khái niệm trong bài hoặc chủ đề AI/product gần khoá. "
                "Thử hỏi lại về LLM, Transformer, RAG, Agent, Problem Statement…"
            ),
        )

    # --- 3) Linh tinh ---
    return ScopeDecision(
        in_scope=False,
        reason="Không khớp transcript, không phải chủ đề gần khoá — từ chối.",
        matched_terms=[],
        category="refuse",
        refusal_message=(
            "Câu hỏi này trông **linh tinh / ngoài phạm vi** buổi học. "
            "Mình chỉ trả lời kiến thức bám transcript khoá, hoặc chủ đề AI/product hơi liên quan "
            "(kèm take-note). Hãy hỏi một khái niệm trên slide hoặc nhập **Ngữ cảnh bài học**."
        ),
    )
