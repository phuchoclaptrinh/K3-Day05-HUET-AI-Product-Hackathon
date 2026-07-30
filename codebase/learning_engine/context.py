from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationContext:
    student_latest: str
    history: list[dict[str, str]] = field(default_factory=list)
    topic_hint: str = ""
    day_code: str = ""

    def history_text(self, max_turns: int = 4) -> str:
        chunks: list[str] = []
        for msg in self.history[-(max_turns * 2) :]:
            role = msg.get("role", "unknown")
            content = (msg.get("content") or "").strip()
            if content:
                chunks.append(f"{role.upper()}: {content}")
        return "\n".join(chunks)


def build_context(
    student_message: str,
    history: list[dict[str, str]] | None = None,
    topic_hint: str = "",
    day_code: str = "",
) -> ConversationContext:
    hist = list(history or [])
    return ConversationContext(
        student_latest=student_message.strip(),
        history=hist,
        topic_hint=topic_hint.strip(),
        day_code=day_code.strip(),
    )
