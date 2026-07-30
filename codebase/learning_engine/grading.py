"""Chấm câu hỏi trắc nghiệm và cập nhật understanding score."""

from __future__ import annotations

from typing import Any


def grade_check_answer(
    check: Any,
    selected_option: str,
    current_score: int,
) -> dict[str, Any]:
    """Chấm MCQ và cập nhật understanding_score.

    Đúng → tăng score (tối đa +25, trần 98).
    Sai → giảm nhẹ (tối thiểu -15, sàn 5) và giữ explanation.
    """
    if isinstance(check, dict):
        question = str(check.get("question") or "")
        options = dict(check.get("options") or {})
        correct_option = str(check.get("correct_option") or "")
        explanation = str(check.get("explanation") or "")
    else:
        question = str(getattr(check, "question", "") or "")
        options = dict(getattr(check, "options", {}) or {})
        correct_option = str(getattr(check, "correct_option", "") or "")
        explanation = str(getattr(check, "explanation", "") or "")

    _ = question  # reserved for future use
    choice = (selected_option or "").strip().upper()
    correct = correct_option.strip().upper()
    is_correct = choice == correct and choice in {"A", "B", "C", "D"}
    score = max(0, min(100, int(current_score)))

    if is_correct:
        boost = 25 if score < 70 else 15
        new_score = min(98, score + boost)
        feedback = (
            f"Chính xác! Đáp án {correct}. "
            + (explanation or "Bạn đã chọn đúng ý cốt lõi.")
        )
    else:
        new_score = max(5, score - 15)
        right_text = options.get(correct, "")
        feedback = (
            f"Chưa đúng. Đáp án phù hợp là {correct}"
            + (f": {right_text}" if right_text else ".")
            + (" " + explanation if explanation else "")
        )

    return {
        "is_correct": is_correct,
        "selected_option": choice,
        "correct_option": correct,
        "previous_score": score,
        "updated_score": new_score,
        "delta": new_score - score,
        "feedback": feedback.strip(),
        "understood": is_correct,
    }
