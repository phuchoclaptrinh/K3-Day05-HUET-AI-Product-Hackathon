"""Flow Lab — chạy kiểm tra luồng với ưu tiên dữ liệu local trước API.

Thứ tự lookup:
1. Cache phiên / đĩa (`.flow_cache.json`) — kết quả đã chạy trước
2. Golden set (`eval/golden-set.jsonl`) — case lab đã biết → chạy local (rule + template)
3. Miss → gọi LearningEngine (API Gemini nếu có key)
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pipeline import LearningEngine, TurnResult
from .strategy import select_strategy
from .followup import _template_followup
from .context import build_context
from .estimator import EstimateResult
from .response import _template_response

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = ROOT / "eval" / "golden-set.jsonl"
CACHE_PATH = Path(__file__).resolve().parents[1] / ".flow_cache.json"

BAND_SCORE = {"low": 25, "mid": 55, "high": 82}


def normalize_key(text: str, topic_hint: str = "") -> str:
    raw = f"{topic_hint.strip()}||{text.strip()}".lower()
    raw = unicodedata.normalize("NFKC", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


@dataclass
class StepTrace:
    step: str
    source: str  # cache | golden_set | rule | api | template | local
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class FlowLabResult:
    cache_key: str
    overall_source: str  # cache | golden_set | api
    api_called: bool
    steps: list[StepTrace]
    result: dict[str, Any]
    matched_case_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cache_key": self.cache_key,
            "overall_source": self.overall_source,
            "api_called": self.api_called,
            "matched_case_id": self.matched_case_id,
            "steps": [asdict(s) for s in self.steps],
            "result": self.result,
        }


def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def load_cache() -> dict[str, Any]:
    data = _load_json(CACHE_PATH, {"entries": {}})
    if "entries" not in data:
        data = {"entries": {}}
    return data


def save_cache_entry(key: str, payload: dict[str, Any]) -> None:
    cache = load_cache()
    cache["entries"][key] = {
        **payload,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def load_golden_cases() -> list[dict[str, Any]]:
    if not GOLDEN_PATH.exists():
        return []
    cases = []
    for line in GOLDEN_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            cases.append(json.loads(line))
    return cases


def find_golden_match(question: str, topic_hint: str = "") -> dict[str, Any] | None:
    q_norm = normalize_key(question)
    topic = topic_hint.strip().lower()
    best: dict[str, Any] | None = None
    best_score = 0.0

    for case in load_golden_cases():
        msg = case.get("student_message") or ""
        msg_norm = normalize_key(msg)
        if not msg_norm:
            continue
        score = 0.0
        if q_norm == msg_norm:
            score = 1.0
        elif q_norm in msg_norm or msg_norm in q_norm:
            score = 0.85
        else:
            # token overlap nhẹ
            q_tokens = set(re.findall(r"[\wÀ-ỹ]+", q_norm))
            m_tokens = set(re.findall(r"[\wÀ-ỹ]+", msg_norm))
            if q_tokens and m_tokens:
                score = len(q_tokens & m_tokens) / max(len(q_tokens), 1)
                if score < 0.72:
                    continue
                score = min(score, 0.8)
            else:
                continue

        # bonus nếu topic khớp notes/tag
        blob = f"{case.get('notes','')} {case.get('tag','')}".lower()
        if topic and topic in blob:
            score += 0.05

        if score > best_score:
            best_score = score
            best = case

    if best and best_score >= 0.72:
        return best
    return None


def _pack_local_from_golden(
    question: str,
    topic_hint: str,
    case: dict[str, Any],
) -> TurnResult:
    band = case.get("expected_band", "low")
    score = BAND_SCORE.get(band, 30)
    expect_empty = bool(case.get("expect_empty_misconceptions", True))
    misconceptions: list[str] = []
    if not expect_empty:
        # gợi ý misconception từ notes/tag — không bịa nội dung học thuật mới
        note = (case.get("notes") or case.get("tag") or "misconception").strip()
        misconceptions = [f"Fixture lab: {note[:120]}"]

    confidence = "low" if band == "low" else ("high" if band == "high" else "medium")
    estimate = EstimateResult(
        understanding_score=score,
        understanding_reason=(
            f"Khớp dữ liệu local golden-set `{case.get('id')}` "
            f"(expected_band={band}). Không gọi API."
        ),
        confidence=confidence,  # type: ignore[arg-type]
        misconceptions=misconceptions,
        provider="golden_set",
    )
    strategy = select_strategy(score, confidence, misconceptions)
    ctx = build_context(question, history=[], topic_hint=topic_hint)
    follow = _template_followup(
        ctx, strategy.teaching_strategy, misconceptions, score
    )
    response = _template_response(ctx, estimate, strategy, follow)
    return LearningEngine._pack(
        estimate,
        strategy,
        [follow],
        response,
        "template",
        "template",
    )


def run_flow_lab(
    question: str,
    topic_hint: str = "",
    force_api: bool = False,
) -> FlowLabResult:
    """Chạy 1 câu hỏi theo thứ tự: cache → golden → API."""
    key = normalize_key(question, topic_hint)
    steps: list[StepTrace] = []

    steps.append(
        StepTrace(
            step="1. Context Builder",
            source="local",
            detail="Ghép student message + topic_hint (không gọi API).",
            data={"topic_hint": topic_hint, "question_preview": question[:160]},
        )
    )

    # --- 1) Cache đĩa ---
    if not force_api:
        cache = load_cache()
        hit = cache.get("entries", {}).get(key)
        if hit and hit.get("result"):
            steps.append(
                StepTrace(
                    step="2. Lookup cache",
                    source="cache",
                    detail=f"HIT cache đĩa ({CACHE_PATH.name}). Bỏ qua API.",
                    data={"saved_at": hit.get("saved_at"), "key": key[:80]},
                )
            )
            result = hit["result"]
            steps.append(
                StepTrace(
                    step="3. Understanding Estimator",
                    source="cache",
                    detail="Đọc score/misconception từ cache.",
                    data={
                        "score": result.get("understanding_score"),
                        "confidence": result.get("confidence"),
                        "provider": result.get("provider_estimate"),
                    },
                )
            )
            steps.append(
                StepTrace(
                    step="4. Teaching Strategy",
                    source="rule",
                    detail="Rule-based (đã lưu trong kết quả cache).",
                    data={"strategy": result.get("teaching_strategy")},
                )
            )
            steps.append(
                StepTrace(
                    step="5. Follow-up Generator",
                    source=result.get("provider_followup", "cache"),
                    detail="Đọc follow-up từ cache.",
                    data={"follow_ups": result.get("follow_ups")},
                )
            )
            steps.append(
                StepTrace(
                    step="6. Tutor Response",
                    source=result.get("provider_response", "cache"),
                    detail="Đọc câu trả lời từ cache.",
                    data={"preview": (result.get("tutor_response") or "")[:180]},
                )
            )
            return FlowLabResult(
                cache_key=key,
                overall_source="cache",
                api_called=False,
                steps=steps,
                result=result,
                matched_case_id=hit.get("matched_case_id"),
            )
        steps.append(
            StepTrace(
                step="2. Lookup cache",
                source="cache",
                detail="MISS — chưa có trong cache đĩa.",
                data={"key": key[:80]},
            )
        )
    else:
        steps.append(
            StepTrace(
                step="2. Lookup cache",
                source="local",
                detail="Bỏ qua cache vì đang force gọi API.",
                data={},
            )
        )

    # --- 2) Golden set ---
    if not force_api:
        golden = find_golden_match(question, topic_hint)
        if golden:
            steps.append(
                StepTrace(
                    step="3. Lookup golden-set",
                    source="golden_set",
                    detail=(
                        f"HIT `{golden.get('id')}` "
                        f"(turn={golden.get('source_turn')}). Dùng fixture local."
                    ),
                    data={
                        "id": golden.get("id"),
                        "expected_band": golden.get("expected_band"),
                        "expect_empty_misconceptions": golden.get(
                            "expect_empty_misconceptions"
                        ),
                        "notes": golden.get("notes"),
                    },
                )
            )
            packed = _pack_local_from_golden(question, topic_hint, golden)
            result = packed.to_dict()
            steps.append(
                StepTrace(
                    step="4. Understanding Estimator",
                    source="golden_set",
                    detail="Suy ra score từ expected_band của golden-set (không API).",
                    data={
                        "score": result["understanding_score"],
                        "confidence": result["confidence"],
                        "misconceptions": result["misconceptions"],
                    },
                )
            )
            steps.append(
                StepTrace(
                    step="5. Teaching Strategy",
                    source="rule",
                    detail="Rule-based theo score / misconception.",
                    data={"strategy": result["teaching_strategy"]},
                )
            )
            steps.append(
                StepTrace(
                    step="6. Follow-up + Response",
                    source="template",
                    detail="Template local (Flow Lab tiết kiệm quota khi khớp golden).",
                    data={"follow_ups": result["follow_ups"]},
                )
            )
            save_cache_entry(
                key,
                {"result": result, "matched_case_id": golden.get("id"), "source": "golden_set"},
            )
            return FlowLabResult(
                cache_key=key,
                overall_source="golden_set",
                api_called=False,
                steps=steps,
                result=result,
                matched_case_id=golden.get("id"),
            )
        steps.append(
            StepTrace(
                step="3. Lookup golden-set",
                source="golden_set",
                detail=f"MISS — không khớp case trong {GOLDEN_PATH.name}.",
                data={"path": str(GOLDEN_PATH)},
            )
        )
    else:
        steps.append(
            StepTrace(
                step="3. Lookup golden-set",
                source="local",
                detail="Bỏ qua golden-set vì đang force gọi API.",
                data={},
            )
        )

    # --- 3) API ---
    steps.append(
        StepTrace(
            step="4. Gọi Learning Engine (API)",
            source="api",
            detail="Không có dữ liệu local phù hợp → gọi Gemini (nếu có key).",
            data={},
        )
    )
    engine = LearningEngine()
    packed = engine.run(question, history=[], topic_hint=topic_hint)
    result = packed.to_dict()

    steps.append(
        StepTrace(
            step="5. Understanding Estimator",
            source=result.get("provider_estimate", "api"),
            detail="Ước lượng mức hiểu + misconception.",
            data={
                "score": result["understanding_score"],
                "confidence": result["confidence"],
                "misconceptions": result["misconceptions"],
                "reason": result["understanding_reason"],
            },
        )
    )
    steps.append(
        StepTrace(
            step="6. Teaching Strategy",
            source="rule",
            detail="Rule-based — không gọi API.",
            data={"strategy": result["teaching_strategy"]},
        )
    )
    steps.append(
        StepTrace(
            step="7. Follow-up Generator",
            source=result.get("provider_followup", "api"),
            detail="Sinh câu hỏi kiểm tra.",
            data={"follow_ups": result["follow_ups"]},
        )
    )
    steps.append(
        StepTrace(
            step="8. Tutor Response",
            source=result.get("provider_response", "api"),
            detail="Sinh câu trả lời theo strategy.",
            data={"preview": (result.get("tutor_response") or "")[:180]},
        )
    )

    save_cache_entry(key, {"result": result, "matched_case_id": None, "source": "api"})
    return FlowLabResult(
        cache_key=key,
        overall_source="api",
        api_called=True,
        steps=steps,
        result=result,
        matched_case_id=None,
    )


def cache_stats() -> dict[str, int]:
    cache = load_cache()
    entries = cache.get("entries", {})
    by_source: dict[str, int] = {"total": len(entries)}
    for item in entries.values():
        src = item.get("source") or "unknown"
        by_source[src] = by_source.get(src, 0) + 1
    return by_source
