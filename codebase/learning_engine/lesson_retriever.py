"""Lesson / Slide Context Retriever.

Hackathon pack không có file slide PDF — dùng transcript sạch như nguồn
ngữ cảnh bài học (tương đương nội dung slide + lời giảng).

Pipeline:
  topic_hint + student_message + session_id
    → tìm các đoạn transcript liên quan
    → lesson_excerpt đưa vào Context cho Estimator / MCQ / Response / Take-note
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

SESSION_CATALOG: list[dict[str, str]] = [
    {
        "id": "t01",
        "file": "transcript-01-clean.md",
        "label": "Day 2 sáng — Xác định bài toán kinh doanh cho AI",
    },
    {
        "id": "t02",
        "file": "transcript-02-clean.md",
        "label": "Day 2 — Chỉ số thành công & mức tự động hoá",
    },
    {
        "id": "t03",
        "file": "transcript-03-clean.md",
        "label": "Day 2 chiều — Soi bài toán · tự động hoá & ràng buộc",
    },
    {
        "id": "t04",
        "file": "transcript-04-clean.md",
        "label": "Day 1 — Foundation: LLM · Transformer · Attention",
    },
    {
        "id": "t05",
        "file": "transcript-05-clean.md",
        "label": "Buổi bài toán · đánh giá · data & product lifecycle",
    },
    {
        "id": "t06",
        "file": "transcript-06-clean.md",
        "label": "Foundation — Transformer · self-attention · token",
    },
]


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKC", (text or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def _tokens(text: str) -> set[str]:
    stop = {
        "theo", "các", "một", "những", "trong", "với", "được", "như", "khi",
        "này", "đó", "của", "và", "cho", "là", "có", "không", "rất", "cũng",
        "bạn", "mình", "chúng", "thì", "để", "từ", "hay", "về", "sau", "trước",
        "the", "and", "for", "with", "that", "this", "from",
        # từ phổ biến dễ khớp nhầm slide (gây false in_lesson)
        "cách", "cach", "làm", "lam", "dùng", "dung", "việc", "viec",
        "nhóm", "nhom", "quản", "quan", "dự", "án", "du", "an",
        "nội", "dung", "phần", "bài", "học", "hoc", "giúp", "giup",
        "muốn", "muon", "cần", "can", "biết", "biet", "hiểu", "hieu",
        "what", "how", "why", "can", "does", "about",
    }
    return {
        t
        for t in re.findall(r"[a-zà-ỹ0-9]{3,}", _norm(text))
        if t not in stop and not t.isdigit()
    }


# Thuật ngữ ngắn vẫn mang nghĩa học thuật (không lọc theo độ dài)
_SHORT_CONTENT = {
    "llm", "rag", "mvp", "api", "rlhf", "odd", "hcd", "jtbd", "qkv", "moe",
    "agent", "token", "prompt", "slide", "eval", "lora",
}


def _content_tokens(text: str) -> set[str]:
    """Token đủ 'nặng' để quyết phạm vi — tránh khớp nhầm từ chung."""
    return {t for t in _tokens(text) if len(t) >= 5 or t in _SHORT_CONTENT}


def _transcript_dir() -> Path | None:
    here = Path(__file__).resolve()
    candidates = [
        here.parents[2] / "data" / "vlearn-pack" / "transcript",
        here.parents[1] / "data" / "vlearn-pack" / "transcript",
        Path.cwd() / "data" / "vlearn-pack" / "transcript",
        Path.cwd().parent / "data" / "vlearn-pack" / "transcript",
    ]
    for c in candidates:
        if c.is_dir():
            return c
    return None


@dataclass
class LessonChunk:
    session_id: str
    session_label: str
    heading: str
    text: str
    cite: str = ""

    def preview(self, n: int = 220) -> str:
        t = re.sub(r"\s+", " ", self.text).strip()
        return t if len(t) <= n else t[: n - 1] + "…"


@dataclass
class LessonContext:
    session_id: str = ""
    session_label: str = ""
    excerpt: str = ""
    sources: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)
    overlap_ratio: float = 0.0  # student vs excerpt (phát hiện dán slide)
    chunk_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def prompt_block(self, max_chars: int = 2800) -> str:
        if not self.excerpt:
            return "(không có excerpt bài học)"
        body = self.excerpt.strip()
        if len(body) > max_chars:
            body = body[: max_chars - 1] + "…"
        heads = ", ".join(self.headings[:4]) if self.headings else "(không rõ)"
        src = ", ".join(self.sources[:6]) if self.sources else "—"
        return (
            f"SESSION: {self.session_label or self.session_id or '(auto)'}\n"
            f"HEADINGS: {heads}\n"
            f"SOURCES: {src}\n"
            f"EXCERPT:\n{body}"
        )


def list_sessions() -> list[dict[str, str]]:
    """Transcript mặc định + PDF slide đã upload (option unique cho Streamlit)."""
    from .slide_ingest import list_uploaded_sessions

    uploaded = list_uploaded_sessions()
    # Gắn display_label unique — Streamlit selectbox cấm trùng options
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for s in uploaded + list(SESSION_CATALOG):
        item = dict(s)
        base = item.get("label") or item.get("id") or "buổi"
        display = base
        if item.get("source") == "pdf":
            display = f"{base}  ·  {item['id'][-6:]}"
        # đảm bảo unique tuyệt đối
        n = 2
        while display in seen:
            display = f"{base}  ·  {item['id'][-6:]}-{n}"
            n += 1
        seen.add(display)
        item["display"] = display
        out.append(item)
    return out


def clear_lesson_cache() -> None:
    _load_all_chunks.cache_clear()


@lru_cache(maxsize=1)
def _load_all_chunks() -> tuple[LessonChunk, ...]:
    from .slide_ingest import list_uploaded_sessions, user_lessons_md_path

    chunks: list[LessonChunk] = []

    # 1) PDF uploads
    for meta in list_uploaded_sessions():
        path = user_lessons_md_path(meta["file"])
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        chunks.extend(_chunks_from_markdown(text, meta["id"], meta["label"], cite_prefix="PDF"))

    # 2) Built-in transcripts
    root = _transcript_dir()
    if root is not None:
        for meta in SESSION_CATALOG:
            path = root / meta["file"]
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            chunks.extend(
                _chunks_from_markdown(text, meta["id"], meta["label"], cite_prefix="T")
            )
    return tuple(chunks)


def _chunks_from_markdown(
    text: str,
    session_id: str,
    session_label: str,
    cite_prefix: str = "T",
) -> list[LessonChunk]:
    chunks: list[LessonChunk] = []
    parts = re.split(r"(?=^##\s+)", text, flags=re.M)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        hm = re.match(r"^##\s+(.+)$", part, re.M)
        heading = hm.group(1).strip() if hm else "(mở đầu)"
        clean = re.sub(r"^\*\*\[T\d+-\d+\]\*\*\s*", "", part, flags=re.M)
        clean = re.sub(r"\[Hoạt động lớp:[^\]]*\]", " ", clean)
        clean = re.sub(r"\[không nghe rõ\]", " ", clean)
        # Chỉ bỏ title cấp 1 / blockquote meta, giữ ## heading
        clean = re.sub(r"^#\s[^#].+$", " ", clean, flags=re.M)
        clean = re.sub(r"^>\s*.+$", " ", clean, flags=re.M)
        clean = re.sub(r"^##\s+.+$", " ", clean, flags=re.M)  # heading đã lưu riêng
        clean = re.sub(r"\s+", " ", clean).strip()
        if len(clean) < 20:
            continue
        cites = re.findall(r"\[T\d+-\d+\]", part)
        cite = cites[0] if cites else f"{cite_prefix}:{session_id}:{heading[:24]}"
        chunks.append(
            LessonChunk(
                session_id=session_id,
                session_label=session_label,
                heading=heading,
                text=clean[:1800],
                cite=cite,
            )
        )
    return chunks


def _is_definition_query(text: str) -> bool:
    return bool(
        re.search(
            r"là gì|la gi|what is|định nghĩa|dinh nghia|nghĩa là|nghia la",
            text or "",
            flags=re.I,
        )
    )


def _is_agenda_or_toc(chunk: LessonChunk) -> bool:
    """Trang mục lục / agenda — hay chứa keyword nhưng không giải thích."""
    t = _norm(f"{chunk.heading} {chunk.text}")
    if "agenda" in t or "mục lục" in t or "muc luc" in t:
        return True
    if t.count("•") >= 4 or t.count("·") >= 6:
        return True
    # Chuỗi bullet chủ đề ngắn (toc)
    if len(re.findall(r"(?:^|\s)[•·\-]\s*\S+", chunk.text)) >= 5 and len(chunk.text) < 900:
        return True
    return False


def _score_chunk(
    chunk: LessonChunk,
    query_tokens: set[str],
    session_id: str,
    query_text: str = "",
) -> float:
    if not query_tokens:
        return 0.0
    blob = f"{chunk.heading} {chunk.text}"
    blob_tokens = _tokens(blob)
    if not blob_tokens:
        return 0.0
    inter = query_tokens & blob_tokens
    if not inter:
        htoks = _tokens(chunk.heading)
        inter = query_tokens & htoks
        if not inter:
            return 0.0

    score = len(inter) * 3.0 + sum(1.5 for t in inter if len(t) >= 6)
    # Mật độ thuật ngữ query trong trang (tránh hòa điểm nhiều trang cùng nhắc 1 từ)
    density = len(inter) / max(12, len(blob_tokens))
    score += density * 55.0

    # Prefer selected session
    if session_id and chunk.session_id == session_id:
        score *= 1.35
    # Heading overlap boost
    if _tokens(chunk.heading) & query_tokens:
        score *= 1.25

    blob_n = _norm(blob)
    q = query_text or ""
    # Boost trang ĐỊNH NGHĨA / trả lời đúng kiểu "X là gì"
    for t in inter:
        if len(t) < 3:
            continue
        if f"{t} là gì" in blob_n or f"{t} la gi" in blob_n:
            score += 28.0
        if re.search(rf"\b{re.escape(t)}\s+(là|la)\s+(một|mot|an|a|the)\b", blob_n):
            score += 16.0
        if "large language model" in blob_n and t == "llm":
            score += 14.0
        if "mô hình ngôn ngữ" in blob_n and t == "llm":
            score += 12.0

    if _is_definition_query(q):
        if re.search(r"là gì|la gi|định nghĩa|dinh nghia", blob_n):
            score += 10.0
        # Phạt trang agenda/toc khi đang hỏi định nghĩa
        if _is_agenda_or_toc(chunk):
            score *= 0.28
        # Trang mở đầu / cover thường chỉ nhắc tên khoá
        if re.search(r"trang\s*1\b", _norm(chunk.heading)) and len(inter) <= 1:
            score *= 0.55

    return score


def _overlap_ratio(student: str, excerpt: str) -> float:
    """Tỷ lệ token học viên trùng excerpt — cao ≈ dán lại slide/transcript."""
    a = _tokens(student)
    b = _tokens(excerpt)
    if len(a) < 8 or not b:
        return 0.0
    return len(a & b) / max(1, len(a))


def retrieve_lesson_context(
    student_message: str,
    topic_hint: str = "",
    session_id: str = "",
    slide_paste: str = "",
    top_k: int = 3,
) -> LessonContext:
    """Lấy ngữ cảnh bài học.

    Ưu tiên:
    1) slide_paste do user dán (excerpt slide)
    2) retrieve từ transcript theo session + câu hỏi / topic_hint
    """
    paste = (slide_paste or "").strip()
    if paste and len(paste) >= 40:
        overlap = _overlap_ratio(student_message, paste)
        label = next(
            (s["label"] for s in list_sessions() if s["id"] == session_id),
            "Excerpt slide người học cung cấp",
        )
        return LessonContext(
            session_id=session_id or "paste",
            session_label=label,
            excerpt=paste[:3200],
            sources=["user_slide_paste"],
            headings=["(excerpt người học dán)"],
            overlap_ratio=overlap,
            chunk_count=1,
        )

    chunks = _load_all_chunks()
    if not chunks:
        return LessonContext()

    query_text = f"{topic_hint} {student_message}".strip()
    q_tokens = _tokens(query_text)
    # Nếu chọn session nhưng query yếu — lấy vài heading đầu session làm grounding
    scored: list[tuple[float, LessonChunk]] = []
    for ch in chunks:
        if session_id and ch.session_id != session_id:
            continue
        s = _score_chunk(ch, q_tokens, session_id, query_text=query_text)
        if s > 0:
            scored.append((s, ch))

    pool = [c for c in chunks if (not session_id or c.session_id == session_id)]
    if not scored and pool:
        # Fallback: top sections of selected (or first) session
        scored = [(1.0, c) for c in pool[:top_k]]

    if not scored and not session_id:
        # Global fallback: best effort across all
        for ch in chunks:
            s = _score_chunk(ch, q_tokens, "", query_text=query_text)
            if s > 0:
                scored.append((s, ch))
        scored.sort(key=lambda x: x[0], reverse=True)
        scored = scored[:top_k] if scored else [(1.0, c) for c in chunks[:top_k]]

    scored.sort(key=lambda x: x[0], reverse=True)
    picked = [c for _, c in scored[:top_k]]
    if not picked:
        return LessonContext()

    parts: list[str] = []
    sources: list[str] = []
    headings: list[str] = []
    for c in picked:
        headings.append(c.heading)
        sources.append(c.cite or c.session_id)
        parts.append(f"### {c.heading}\n{c.preview(900)}")

    excerpt = "\n\n".join(parts)
    overlap = _overlap_ratio(student_message, excerpt)
    return LessonContext(
        session_id=picked[0].session_id,
        session_label=picked[0].session_label,
        excerpt=excerpt,
        sources=sources,
        headings=headings,
        overlap_ratio=round(overlap, 3),
        chunk_count=len(picked),
    )
