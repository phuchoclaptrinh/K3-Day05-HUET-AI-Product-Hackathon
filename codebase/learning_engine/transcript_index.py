"""Chỉ mục chủ đề từ transcript VLearn — dùng cho Scope Guard 3 mức."""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

# Thuật ngữ / cụm từ cốt lõi xuất hiện trên bài giảng (bổ sung headings động)
CORE_PHRASES = [
    # Day 1 / Foundation / T04–T06
    "llm", "large language model", "mô hình ngôn ngữ", "transformer", "attention",
    "self-attention", "multi-head", "token", "next token", "context", "context window",
    "ngữ cảnh", "embedding", "temperature", "top-k", "top-p", "rlhf", "hallucination",
    "knowledge cutoff", "agent", "ai agent", "evaluation", "eval", "api", "mixture of experts",
    "deep learning", "machine learning", "foundation model", "alphago", "chatgpt",
    "deepseek", "encoder", "decoder", "q-k-v", "qkv",
    # Day 2 / problem / product / T01–T03 / T05
    "bài toán", "yêu cầu mơ hồ", "product manager", "project manager", "product owner",
    "double diamond", "first principle", "first principles", "impact", "effort",
    "impact-effort", "hcd", "human centered", "quick win", "chỉ số thành công",
    "automation", "augmentation", "tự động hoá", "rule-based", "workflow",
    "chaining", "routing", "parallel", "rag", "tool calling", "function calling",
    "fine-tuning", "fine tune", "finetune", "odd", "operational design domain",
    "problem statement", "problem scoping", "baseline", "mvp", "jtbd",
    "ai engineer", "mlops", "ai pm", "vượt", "metric", "stakeholder",
    "deterministic", "chi phí", "bảo mật", "scope",
    # Lab / hệ sinh thái khoá
    "vlearn", "ai thực chiến", "prompt", "prompting", "slide", "kahoot",
    "needle", "haystack", "citation", "grounding",
]

# AI / product / tech gần khoá nhưng có thể không giảng trực tiếp → related_external
RELATED_DOMAIN_TERMS = [
    "gpt", "claude", "gemini", "openai", "anthropic", "bert", "diffusion", "gan",
    "cnn", "rnn", "lstm", "pytorch", "tensorflow", "huggingface", "langchain",
    "langgraph", "vector", "embedding model", "vector db", "pinecone", "chroma",
    "docker", "kubernetes", "sql", "python", "javascript", "fastapi", "streamlit",
    "blockchain", "fintech", "ocr", "computer vision", "nlp", "whisper",
    "copilot", "cursor", "ragas", "langsmith", "mlflow", "lora", "qlora",
    "quantization", "inference", "gpu", "cuda", "saas", "product market fit",
    "okrs", "north star", "a/b test", "ab test", "ux", "ui",
]


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKC", (text or "").lower())
    return re.sub(r"\s+", " ", t).strip()


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


@lru_cache(maxsize=1)
def load_transcript_index() -> dict:
    """Load headings + session labels từ 6 file transcript-*-clean.md."""
    root = _transcript_dir()
    headings: list[str] = []
    sessions: list[dict] = []
    if root is None:
        return {"headings": [], "sessions": [], "phrases": list(CORE_PHRASES), "ok": False}

    for path in sorted(root.glob("transcript-*-clean.md")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        title = ""
        m_title = re.search(r"^#\s+(.+)$", text, re.M)
        if m_title:
            title = m_title.group(1).strip()
        file_heads = re.findall(r"^##\s+(.+)$", text, re.M)
        headings.extend(h.strip() for h in file_heads)
        sessions.append(
            {
                "file": path.name,
                "title": title,
                "headings": [h.strip() for h in file_heads],
            }
        )

    # phrases = core + normalized heading fragments (≥4 chars)
    phrases = list(CORE_PHRASES)
    for h in headings:
        hn = _norm(h)
        phrases.append(hn)
        for part in re.split(r"[:–—,\-/]| và |: ", hn):
            part = part.strip()
            if len(part) >= 4:
                phrases.append(part)

    # unique preserve order
    seen: set[str] = set()
    uniq: list[str] = []
    for p in phrases:
        pn = _norm(p)
        if pn and pn not in seen:
            seen.add(pn)
            uniq.append(pn)

    return {
        "headings": [_norm(h) for h in headings],
        "sessions": sessions,
        "phrases": uniq,
        "ok": True,
    }


def score_against_transcript(text: str, topic_hint: str = "", day_code: str = "") -> dict:
    """Chấm độ khớp với transcript. Trả hits + score 0–100."""
    idx = load_transcript_index()
    blob = _norm(f"{text} {topic_hint} {day_code}")
    if not blob:
        return {"score": 0, "hits": [], "heading_hits": [], "index_ok": idx["ok"]}

    hits: list[str] = []
    heading_hits: list[str] = []

    for h in idx["headings"]:
        # heading overlap: full heading in blob OR ≥2 significant tokens shared
        if len(h) >= 8 and h in blob:
            heading_hits.append(h[:80])
            continue
        tokens = [t for t in re.findall(r"[a-zà-ỹ0-9]{4,}", h) if t not in {"theo", "các", "một", "những", "trong"}]
        shared = [t for t in tokens if t in blob]
        if len(shared) >= 2 or (len(shared) == 1 and len(shared[0]) >= 8):
            heading_hits.append(h[:80])

    for phrase in idx["phrases"]:
        if len(phrase) < 3:
            continue
        if phrase in blob:
            hits.append(phrase)

    # dedupe hits, keep short meaningful ones first
    hits = list(dict.fromkeys(hits))[:12]
    heading_hits = list(dict.fromkeys(heading_hits))[:6]

    score = 0
    score += min(55, 18 * len(heading_hits))
    score += min(40, 8 * min(len(hits), 6))
    if topic_hint and any(_norm(topic_hint) in h or h in _norm(topic_hint) for h in idx["headings"]):
        score += 20
    elif topic_hint and len(_norm(topic_hint)) >= 3:
        # topic_hint có nhưng chưa map heading → vẫn cộng nhẹ (user đang học)
        score += 10

    return {
        "score": min(100, score),
        "hits": hits[:8],
        "heading_hits": heading_hits,
        "index_ok": idx["ok"],
    }


def is_related_domain(text: str) -> bool:
    blob = _norm(text)
    return any(term in blob for term in RELATED_DOMAIN_TERMS)
