from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StrategyResult:
    teaching_strategy: str
    asked_check_question: bool
    need_review: bool = False
    need_example: bool = False
    need_hint: bool = False
    need_check: bool = False
    need_next: bool = False


def select_strategy(
    understanding_score: int,
    confidence: str,
    misconceptions: list[str],
) -> StrategyResult:
    """Rule-based Teaching Strategy Selector (pipeline §3.4)."""
    score = max(0, min(100, int(understanding_score)))
    conf = (confidence or "medium").lower()
    has_misc = bool(misconceptions)

    # Priority: misconception → low confidence → score bands
    if has_misc:
        return StrategyResult(
            teaching_strategy="review_concept",
            asked_check_question=True,
            need_review=True,
            need_check=True,
        )

    if conf == "low":
        return StrategyResult(
            teaching_strategy="validate_understanding",
            asked_check_question=True,
            need_check=True,
        )

    if score < 40:
        return StrategyResult(
            teaching_strategy="review_concept",
            asked_check_question=True,
            need_review=True,
            need_check=True,
        )

    if score < 70:
        return StrategyResult(
            teaching_strategy="give_example",
            asked_check_question=True,
            need_example=True,
            need_check=True,
        )

    if score < 90:
        return StrategyResult(
            teaching_strategy="validate_understanding",
            asked_check_question=True,
            need_check=True,
        )

    return StrategyResult(
        teaching_strategy="next_topic",
        asked_check_question=False,
        need_next=True,
    )


def expected_strategy_from_signals(
    understanding_score: int,
    confidence: str,
    misconceptions: list[str],
) -> str:
    return select_strategy(understanding_score, confidence, misconceptions).teaching_strategy
