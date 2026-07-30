from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .context import ConversationContext, build_context
from .estimator import EstimateResult, estimate_understanding
from .followup import generate_followup
from .response import generate_tutor_response
from .strategy import StrategyResult, select_strategy


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
    tutor_response: str
    provider_estimate: str
    provider_response: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LearningEngine:
    def run(
        self,
        student_message: str,
        history: list[dict[str, str]] | None = None,
        topic_hint: str = "",
        day_code: str = "",
        generate_response: bool = True,
    ) -> TurnResult:
        """generate_response=False bỏ qua call sinh câu trả lời (tiết kiệm quota khi eval)."""
        ctx = build_context(student_message, history, topic_hint, day_code)
        estimate = estimate_understanding(ctx)
        strategy = select_strategy(
            estimate.understanding_score,
            estimate.confidence,
            estimate.misconceptions,
        )
        follow_ups = generate_followup(
            ctx,
            strategy.teaching_strategy,
            estimate.misconceptions,
            estimate.understanding_score,
        )
        if generate_response:
            tutor_response, provider_response = generate_tutor_response(
                ctx, estimate, strategy, follow_ups
            )
        else:
            tutor_response, provider_response = "", "skipped"
        return self._pack(estimate, strategy, follow_ups, tutor_response, provider_response)

    @staticmethod
    def _pack(
        estimate: EstimateResult,
        strategy: StrategyResult,
        follow_ups: list[str],
        tutor_response: str,
        provider_response: str,
    ) -> TurnResult:
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
            tutor_response=tutor_response,
            provider_estimate=estimate.provider,
            provider_response=provider_response,
        )
