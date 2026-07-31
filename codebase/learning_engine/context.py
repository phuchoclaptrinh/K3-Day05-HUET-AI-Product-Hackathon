from __future__ import annotations

from dataclasses import dataclass, field

from .lesson_retriever import LessonContext, retrieve_lesson_context


@dataclass
class ConversationContext:
    student_latest: str
    history: list[dict[str, str]] = field(default_factory=list)
    topic_hint: str = ""
    day_code: str = ""
    session_id: str = ""
    slide_paste: str = ""
    lesson: LessonContext = field(default_factory=LessonContext)

    def history_text(self, max_turns: int = 4) -> str:
        chunks: list[str] = []
        for msg in self.history[-(max_turns * 2) :]:
            role = msg.get("role", "unknown")
            content = (msg.get("content") or "").strip()
            if content:
                chunks.append(f"{role.upper()}: {content}")
        return "\n".join(chunks)

    def lesson_prompt(self) -> str:
        return self.lesson.prompt_block()


def build_context(
    student_message: str,
    history: list[dict[str, str]] | None = None,
    topic_hint: str = "",
    day_code: str = "",
    session_id: str = "",
    slide_paste: str = "",
) -> ConversationContext:
    hist = list(history or [])
    sid = (session_id or day_code or "").strip()
    lesson = retrieve_lesson_context(
        student_message=student_message,
        topic_hint=topic_hint,
        session_id=sid,
        slide_paste=slide_paste,
    )
    return ConversationContext(
        student_latest=student_message.strip(),
        history=hist,
        topic_hint=topic_hint.strip(),
        day_code=day_code.strip(),
        session_id=sid,
        slide_paste=(slide_paste or "").strip(),
        lesson=lesson,
    )
