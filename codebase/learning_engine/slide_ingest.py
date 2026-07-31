"""Ingest PDF slides → lưu thành buổi học có thể chọn trong dropdown.

Lưu tại `codebase/.user_lessons/`:
  index.json
  {lesson_id}.md   # text đã trích (## Trang N)
  {lesson_id}.pdf  # bản gốc (tuỳ chọn giữ)
"""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _lessons_dir() -> Path:
    # learning_engine/ -> codebase/
    root = Path(__file__).resolve().parents[1] / ".user_lessons"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _index_path() -> Path:
    return _lessons_dir() / "index.json"


def _slugify(name: str) -> str:
    t = unicodedata.normalize("NFKD", name or "slide")
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return (t[:40] or "slide")


def load_index() -> list[dict[str, Any]]:
    path = _index_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("lessons") or [])
    except Exception:
        return []


def save_index(lessons: list[dict[str, Any]]) -> None:
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "lessons": lessons,
    }
    _index_path().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def list_uploaded_sessions() -> list[dict[str, str]]:
    """Format giống SESSION_CATALOG: id, label, file, source=pdf."""
    out: list[dict[str, str]] = []
    for item in load_index():
        lid = str(item.get("id") or "").strip()
        if not lid:
            continue
        out.append(
            {
                "id": lid,
                "label": str(item.get("label") or lid),
                "file": str(item.get("md_file") or f"{lid}.md"),
                "source": "pdf",
            }
        )
    return out


def extract_text_from_pdf_bytes(data: bytes) -> tuple[str, int]:
    """Trả (markdown theo trang, số trang). Cần package pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "Thiếu thư viện pypdf. Chạy: pip install pypdf"
        ) from exc

    import io

    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception as exc:
        raise RuntimeError(f"PDF không đọc được: {exc}") from exc

    pages_md: list[str] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            raw = page.extract_text() or ""
        except Exception:
            raw = ""
        raw = re.sub(r"\s+", " ", raw).strip()
        if not raw:
            continue
        pages_md.append(f"## Trang {i}\n\n{raw}")
    if not pages_md:
        raise RuntimeError(
            "Không trích được chữ từ PDF (file scan ảnh / trống). "
            "Thử PDF có text hoặc dán excerpt thủ công."
        )
    return "\n\n".join(pages_md), len(reader.pages)


def ingest_pdf_slide(
    filename: str,
    data: bytes,
    label: str = "",
) -> dict[str, Any]:
    """Lưu PDF + markdown trích xuất, thêm vào index buổi học.

    Nếu cùng `source_filename` đã tồn tại → ghi đè bản cũ (tránh trùng tên trong dropdown).
    """
    if not data:
        raise RuntimeError("File PDF trống.")
    if len(data) > 25 * 1024 * 1024:
        raise RuntimeError("PDF quá lớn (>25MB).")

    md_body, page_count = extract_text_from_pdf_bytes(data)
    stem = _slugify(Path(filename).stem)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    lesson_id = f"pdf_{stem}_{stamp}"
    base_name = (label or Path(filename).stem or lesson_id).strip()
    display = base_name if base_name.startswith("📄") else f"📄 {base_name}"

    root = _lessons_dir()
    md_name = f"{lesson_id}.md"
    pdf_name = f"{lesson_id}.pdf"
    header = (
        f"# {display}\n\n"
        f"> Nguồn: upload PDF `{filename}` · {page_count} trang · "
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
    )
    (root / md_name).write_text(header + md_body, encoding="utf-8")
    (root / pdf_name).write_bytes(data)

    lessons = load_index()
    # Xoá bản cũ cùng tên file nguồn (tránh 4 lần «SLIDE1» làm vỡ selectbox)
    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for x in lessons:
        same_file = str(x.get("source_filename") or "") == filename
        same_label = str(x.get("label") or "") == display
        if same_file or same_label:
            removed.append(x)
        else:
            kept.append(x)
    for old in removed:
        for key in ("md_file", "pdf_file"):
            name = old.get(key)
            if not name:
                continue
            p = root / str(name)
            if p.exists() and p.name not in {md_name, pdf_name}:
                try:
                    p.unlink()
                except OSError:
                    pass
    lessons = kept

    meta = {
        "id": lesson_id,
        "label": display,
        "md_file": md_name,
        "pdf_file": pdf_name,
        "source_filename": filename,
        "page_count": page_count,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "char_count": len(md_body),
    }
    lessons.insert(0, meta)
    save_index(lessons)

    try:
        from .lesson_retriever import clear_lesson_cache

        clear_lesson_cache()
    except Exception:
        pass

    return meta


def delete_uploaded_lesson(lesson_id: str) -> bool:
    lessons = load_index()
    target = next((x for x in lessons if x.get("id") == lesson_id), None)
    if not target:
        return False
    root = _lessons_dir()
    for key in ("md_file", "pdf_file"):
        name = target.get(key)
        if name:
            p = root / str(name)
            if p.exists():
                p.unlink()
    lessons = [x for x in lessons if x.get("id") != lesson_id]
    save_index(lessons)
    try:
        from .lesson_retriever import clear_lesson_cache

        clear_lesson_cache()
    except Exception:
        pass
    return True


def user_lessons_md_path(md_file: str) -> Path:
    return _lessons_dir() / md_file
