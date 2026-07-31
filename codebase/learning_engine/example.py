"""Example Illustrator — sinh 1 ví dụ minh họa gắn với khái niệm học viên đang hỏi."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from .context import ConversationContext
from .llm_client import call_llm_json, resolve_mode

SYSTEM_PROMPT = """Bạn là trợ giảng VLearn. Sinh ĐÚNG 1 ví dụ minh họa ngắn tiếng Việt
cho khái niệm học viên đang hỏi, BÁM LESSON_EXCERPT (nội dung buổi học).

Trả JSON:
{
  "title": "<tên ví dụ ≤8 từ>",
  "scenario": "<1–2 câu tình huống đời thường hoặc sản phẩm>",
  "mapping": "<1–2 câu nối tình huống với khái niệm kỹ thuật trong bài>",
  "takeaway": "<1 câu ý cần nhớ>"
}

Quy tắc:
- Ví dụ cụ thể, dễ hình dung; không dài dòng.
- Ưu tiên ánh xạ đúng ý trong LESSON_EXCERPT / topic_hint.
- Không lộ đáp án câu trắc nghiệm.
- Không bịa số liệu nghiên cứu giả.
"""


@dataclass
class ExampleIllustration:
    title: str
    scenario: str
    mapping: str
    takeaway: str
    provider: str = "template"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def markdown(self) -> str:
        return (
            "---\n"
            "### Ví dụ minh họa (trong bài học)\n"
            f"**{self.title}**\n\n"
            f"{self.scenario}\n\n"
            f"*Ánh xạ:* {self.mapping}\n\n"
            f"*Ý nhớ:* {self.takeaway}"
        )


def _topic(ctx: ConversationContext) -> str:
    if ctx.topic_hint:
        return ctx.topic_hint[:80]
    text = re.sub(r"^\(Trang[^)]*\)\s*", "", ctx.student_latest).strip()
    return (text[:80] + ("..." if len(text) > 80 else "")) or "khái niệm đang học"


def _template_example(ctx: ConversationContext) -> ExampleIllustration:
    topic = _topic(ctx)
    t = topic.lower()
    if "transformer" in t or "attention" in t:
        return ExampleIllustration(
            title="Đọc cả trang thay vì từng dòng",
            scenario=(
                "Khi đọc một đoạn chat dài, bạn có thể nhìn toàn bộ tin nhắn để hiểu "
                "ai đang nói với ai — không cần đọc tuần tự từng chữ rồi quên phần đầu."
            ),
            mapping=(
                "Transformer dùng self-attention để 'nhìn' nhiều vị trí trong câu cùng lúc, "
                "khác RNN phải đi từng bước."
            ),
            takeaway="Attention = nhìn quan hệ toàn cục; không bị kẹt xử lý tuần tự.",
            provider="template",
        )
    if "mvp" in t:
        return ExampleIllustration(
            title="Quán ăn thử món trước khi mở chuỗi",
            scenario=(
                "Trước khi thuê mặt bằng lớn, bạn mở một gian hàng nhỏ bán 2–3 món "
                "để xem khách có quay lại không."
            ),
            mapping=(
                "MVP là phiên bản tối giản đủ để kiểm chứng giả thuyết với người dùng thật "
                "trước khi đầu tư full."
            ),
            takeaway="MVP = học từ người dùng thật với chi phí thấp, không phải sản phẩm hoàn thiện.",
            provider="template",
        )
    if "rag" in t or "retrieval" in t:
        return ExampleIllustration(
            title="Mang tài liệu vào buổi họp",
            scenario=(
                "Trước khi trả lời sếp, bạn mở đúng file quy trình liên quan rồi trả lời "
                "theo tài liệu đó."
            ),
            mapping="RAG truy xuất đoạn tài liệu liên quan rồi mới để LLM trả lời có căn cứ.",
            takeaway="RAG = tìm rồi trả lời, giảm bịa nguồn.",
            provider="template",
        )
    if "prompt" in t:
        return ExampleIllustration(
            title="Giao việc rõ cho thực tập sinh",
            scenario=(
                "Thay vì nói 'làm giúp cái này', bạn nêu vai trò, đầu vào, định dạng đầu ra "
                "và ví dụ."
            ),
            mapping="Prompt tốt = role + task + context + format — giảm câu trả lời lạc đề.",
            takeaway="Càng rõ ràng đầu vào, đầu ra càng đúng cỡ.",
            provider="template",
        )
    if "context" in t or "ngữ cảnh" in t:
        return ExampleIllustration(
            title="Bàn làm việc có giới hạn chỗ",
            scenario=(
                "Bàn chỉ để được một chồng tài liệu; thêm quá nhiều thì phải bỏ bớt tờ cũ."
            ),
            mapping="Context window là giới hạn token model 'nhìn' được mỗi lần suy luận.",
            takeaway="Context có hạn — cần chọn đúng thông tin đưa vào.",
            provider="template",
        )

    return ExampleIllustration(
        title=f"Ví dụ gắn với «{topic}»",
        scenario=(
            f"Hình dung bạn đang giải thích «{topic}» cho một bạn cùng lớp bằng một tình huống "
            "quen thuộc trong 30 giây."
        ),
        mapping=f"Mọi chi tiết trong tình huống phải map được sang đúng ý của «{topic}».",
        takeaway="Hiểu thật = kể lại được bằng ví dụ, không chỉ nhắc định nghĩa.",
        provider="template",
    )


def generate_example(
    ctx: ConversationContext,
    misconceptions: list[str] | None = None,
    teaching_strategy: str = "",
    use_llm: bool = True,
) -> ExampleIllustration:
    mode = resolve_mode()
    if use_llm and mode != "mock":
        user = f"""TOPIC_HINT: {ctx.topic_hint or "(không có)"}
STUDENT: {ctx.student_latest}
STRATEGY: {teaching_strategy or "(không có)"}
MISCONCEPTIONS: {misconceptions or []}

LESSON_CONTEXT:
{ctx.lesson_prompt()}
"""
        try:
            data, provider = call_llm_json(SYSTEM_PROMPT, user)
            title = str(data.get("title") or "").strip()
            scenario = str(data.get("scenario") or "").strip()
            mapping = str(data.get("mapping") or "").strip()
            takeaway = str(data.get("takeaway") or "").strip()
            if title and scenario and mapping and takeaway:
                return ExampleIllustration(
                    title=title,
                    scenario=scenario,
                    mapping=mapping,
                    takeaway=takeaway,
                    provider=provider,
                )
        except Exception:
            pass
    return _template_example(ctx)
