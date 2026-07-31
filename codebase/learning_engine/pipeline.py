from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .context import ConversationContext, build_context
from .estimator import EstimateResult, estimate_understanding
from .example import ExampleIllustration, generate_example
from .followup import CheckQuestion, generate_followup, _template_check_question
from .response import generate_tutor_response
from .scope_guard import ScopeDecision, TAKE_NOTE_EXTERNAL, check_scope
from .strategy import StrategyResult, select_strategy


def _enrich_take_note(scope: ScopeDecision, ctx: ConversationContext) -> str:
    """Take-note ngoài bài: nêu rõ buổi học đang bám + heading liên quan."""
    if scope.category != "related_external":
        return scope.take_note
    heads = ", ".join(ctx.lesson.headings[:2]) if ctx.lesson.headings else ""
    session = ctx.lesson.session_label or "transcript khoá"
    extra = (
        f" Buổi đang tham chiếu: «{session}»"
        + (f" · mục gần nhất: {heads}." if heads else ".")
    )
    base = scope.take_note or TAKE_NOTE_EXTERNAL
    if "Buổi đang tham chiếu" in base:
        return base
    return base.rstrip() + extra


@dataclass
class TurnResult:
    understanding_score: int
    understanding_reason: str
    confidence: str
    misconceptions: list[str]
    teaching_strategy: str
    asked_check_question: bool
    need_review: bool
    need_example: bool
    need_hint: bool
    need_check: bool
    need_next: bool
    follow_ups: list[str]
    check_question: dict[str, Any] | None
    tutor_response: str
    provider_estimate: str
    provider_followup: str
    provider_response: str
    # Scope + example
    in_scope: bool = True
    scope_category: str = "in_lesson"
    scope_reason: str = ""
    scope_matched_terms: list[str] = field(default_factory=list)
    scope_take_note: str = ""
    transcript_score: int = 0
    heading_hits: list[str] = field(default_factory=list)
    example: dict[str, Any] | None = None
    provider_example: str = "skipped"
    api_calls_skipped: bool = False
    # Lesson / slide context
    lesson_session: str = ""
    lesson_headings: list[str] = field(default_factory=list)
    lesson_sources: list[str] = field(default_factory=list)
    lesson_excerpt_preview: str = ""
    lesson_overlap_ratio: float = 0.0
    # Understanding matrix (4 trục + comment)
    understanding_matrix: dict[str, Any] = field(default_factory=dict)
    matrix_comment: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LearningEngine:
    def run(
        self,
        student_message: str,
        history: list[dict[str, str]] | None = None,
        topic_hint: str = "",
        day_code: str = "",
        session_id: str = "",
        slide_paste: str = "",
        generate_response: bool = True,
        generate_followup_llm: bool = True,
        generate_example_llm: bool = True,
        enforce_scope: bool = True,
    ) -> TurnResult:
        """session_id / slide_paste: ngữ cảnh bài học (transcript hoặc excerpt dán)."""
        sid = (session_id or day_code or "").strip()

        # --- 0) Context + Lesson Retriever trước — để Scope Guard biết slide PDF ---
        ctx = build_context(
            student_message,
            history,
            topic_hint,
            day_code=sid,
            session_id=sid,
            slide_paste=slide_paste,
        )

        # --- 1) Scope Guard (có xét excerpt slide đã chọn) ---
        scope = check_scope(student_message, topic_hint, sid, lesson=ctx.lesson)
        if enforce_scope and not scope.in_scope:
            return self._out_of_scope_pack(scope)

        take_note = _enrich_take_note(scope, ctx)

        estimate = estimate_understanding(ctx)
        strategy = select_strategy(
            estimate.understanding_score,
            estimate.confidence,
            estimate.misconceptions,
        )

        example: ExampleIllustration | None = None
        provider_example = "skipped"
        if generate_response and scope.category == "in_lesson":
            example = generate_example(
                ctx,
                misconceptions=estimate.misconceptions,
                teaching_strategy=strategy.teaching_strategy,
                use_llm=generate_example_llm,
            )
            provider_example = example.provider

        if generate_followup_llm:
            follow_ups, provider_followup, check_q = generate_followup(
                ctx,
                strategy.teaching_strategy,
                estimate.misconceptions,
                estimate.understanding_score,
                understanding_reason=estimate.understanding_reason,
                confidence=estimate.confidence,
            )
        else:
            check_q = _template_check_question(
                ctx,
                strategy.teaching_strategy,
                estimate.misconceptions,
                estimate.understanding_score,
            )
            follow_ups = [check_q.stem_for_eval()]
            provider_followup = "template"

        if generate_response:
            tutor_response, provider_response = generate_tutor_response(
                ctx,
                estimate,
                strategy,
                follow_ups,
                check_question=check_q,
                example=example,
                take_note=take_note,
            )
        else:
            tutor_response, provider_response = "", "skipped"

        # Gắn take_note đã enrich vào scope để UI đọc
        scope.take_note = take_note

        return self._pack(
            estimate,
            strategy,
            follow_ups,
            check_q,
            tutor_response,
            provider_followup,
            provider_response,
            scope=scope,
            example=example,
            provider_example=provider_example,
            ctx=ctx,
        )

    @staticmethod
    def _out_of_scope_pack(scope: ScopeDecision) -> TurnResult:
        return TurnResult(
            understanding_score=0,
            understanding_reason="Ngoài phạm vi khoá — không ước lượng hiểu bài.",
            confidence="high",
            misconceptions=[],
            teaching_strategy="out_of_scope",
            asked_check_question=False,
            need_review=False,
            need_example=False,
            need_hint=False,
            need_check=False,
            need_next=False,
            follow_ups=[],
            check_question=None,
            tutor_response=scope.refusal_message,
            provider_estimate="skipped",
            provider_followup="skipped",
            provider_response="scope_guard",
            in_scope=False,
            scope_category=scope.category,
            scope_reason=scope.reason,
            scope_matched_terms=list(scope.matched_terms),
            scope_take_note="",
            transcript_score=scope.transcript_score,
            heading_hits=list(scope.heading_hits),
            example=None,
            provider_example="skipped",
            api_calls_skipped=True,
        )

    @staticmethod
    def _pack(
        estimate: EstimateResult,
        strategy: StrategyResult,
        follow_ups: list[str],
        check_question: CheckQuestion | None,
        tutor_response: str,
        provider_followup: str,
        provider_response: str,
        scope: ScopeDecision | None = None,
        example: ExampleIllustration | None = None,
        provider_example: str = "skipped",
        ctx: ConversationContext | None = None,
    ) -> TurnResult:
        scope = scope or ScopeDecision(
            in_scope=True,
            reason="enforce_scope=False hoặc mặc định.",
            matched_terms=[],
            category="in_lesson",
        )
        lesson = ctx.lesson if ctx else None
        preview = ""
        if lesson and lesson.excerpt:
            preview = lesson.excerpt[:420] + ("…" if len(lesson.excerpt) > 420 else "")
        return TurnResult(
            understanding_score=estimate.understanding_score,
            understanding_reason=estimate.understanding_reason,
            confidence=estimate.confidence,
            misconceptions=list(estimate.misconceptions),
            teaching_strategy=strategy.teaching_strategy,
            asked_check_question=strategy.asked_check_question,
            need_review=strategy.need_review,
            need_example=strategy.need_example,
            need_hint=strategy.need_hint,
            need_check=strategy.need_check,
            need_next=strategy.need_next,
            follow_ups=follow_ups,
            check_question=check_question.to_dict() if check_question else None,
            tutor_response=tutor_response,
            provider_estimate=estimate.provider,
            provider_followup=provider_followup,
            provider_response=provider_response,
            in_scope=scope.in_scope,
            scope_category=scope.category,
            scope_reason=scope.reason,
            scope_matched_terms=list(scope.matched_terms),
            scope_take_note=scope.take_note,
            transcript_score=scope.transcript_score,
            heading_hits=list(scope.heading_hits),
            example=example.to_dict() if example else None,
            provider_example=provider_example,
            api_calls_skipped=False,
            lesson_session=(lesson.session_label if lesson else "") or "",
            lesson_headings=list(lesson.headings) if lesson else [],
            lesson_sources=list(lesson.sources) if lesson else [],
            lesson_excerpt_preview=preview,
            lesson_overlap_ratio=float(lesson.overlap_ratio) if lesson else 0.0,
            understanding_matrix=estimate.matrix_dict(),
            matrix_comment=estimate.matrix_comment or "",
        )
