#!/usr/bin/env python3
"""Run golden-set eval (CP3 — lượt đo).

Usage (from repo root):
  python eval/run_eval.py
  python eval/run_eval.py --run 1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODEBASE = ROOT / "codebase"
sys.path.insert(0, str(CODEBASE))

from learning_engine.llm_client import resolve_mode  # noqa: E402
from learning_engine.pipeline import LearningEngine  # noqa: E402
from learning_engine.strategy import expected_strategy_from_signals  # noqa: E402

GOLDEN = ROOT / "eval" / "golden-set.jsonl"
QUALITY_BAR_PCT = 70


def band_of(score: int) -> str:
    if score < 40:
        return "low"
    if score <= 70:
        return "mid"
    return "high"


def load_golden(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def eval_case(engine: LearningEngine, case: dict) -> dict:
    result = engine.run(
        case["student_message"],
        history=case.get("history") or [],
        generate_response=False,
        generate_followup_llm=False,  # eval Q3 chỉ cần có câu hỏi; tiết kiệm quota
    )
    score = result.understanding_score
    conf = result.confidence
    misc = result.misconceptions
    move = result.teaching_strategy
    follow = result.follow_ups

    # Q1: khớp band nghiêm ngặt theo eval/README.md (không nới biên)
    expected_band = case["expected_band"]
    actual_band = band_of(score)
    q1 = actual_band == expected_band

    expected_move = expected_strategy_from_signals(score, conf, misc)
    q2 = move == expected_move

    need_follow = score < 90 or bool(misc)
    q3 = (not need_follow) or (
        len(follow) == 1 and follow[0].strip().endswith("?")
    ) or (len(follow) == 1 and "?" in follow[0])

    expect_empty = bool(case.get("expect_empty_misconceptions", True))
    if expect_empty:
        q4 = len(misc) == 0
    else:
        q4 = len(misc) > 0  # must detect something when we expect misconception signal

    # Q4 "không bịa" is the hard bar dimension when expect_empty
    q4_hallucination = (not expect_empty) or (len(misc) == 0)

    passed = q1 and q2 and q3 and q4
    return {
        "id": case["id"],
        "source_turn": case.get("source_turn"),
        "layer": case.get("layer"),
        "pass": passed,
        "q1_band": q1,
        "q2_move": q2,
        "q3_followup": q3,
        "q4_misconception": q4,
        "q4_no_hallucination": q4_hallucination,
        "score": score,
        "band_actual": actual_band,
        "band_expected": expected_band,
        "confidence": conf,
        "move": move,
        "misconceptions": misc,
        "follow_ups": follow,
        "provider": result.provider_estimate,
        "reason": result.understanding_reason,
    }


def render_md(rows: list[dict], run_id: int, mode: str) -> str:
    n = len(rows)
    n_pass = sum(1 for r in rows if r["pass"])
    pct = round(100.0 * n_pass / n, 1) if n else 0.0
    q4_fail = [r for r in rows if not r["q4_no_hallucination"]]
    n_real = sum(1 for r in rows if r["provider"] in {"gemini", "openai"})
    n_fallback = n - n_real
    bar_ok = pct >= QUALITY_BAR_PCT and len(q4_fail) == 0

    lines = [
        f"# Eval results — run {run_id}",
        "",
        f"- Thời điểm: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Provider / mode: `{mode}` · model: `{os.getenv('GEMINI_MODEL', 'n/a')}`",
        f"- Golden set: `{GOLDEN.as_posix()}` ({n} cases)",
        f"- Case chạy bằng **LLM thật**: **{n_real}/{n}** · fallback heuristic: **{n_fallback}/{n}**",
        f"- Quality bar: **≥{QUALITY_BAR_PCT}% pass** AND **0 case bịa misconception (Q4 khi expect empty)**",
        f"- Kết quả: **{n_pass}/{n} = {pct}%** → {'ĐẠT bar' if bar_ok else 'CHƯA ĐẠT bar'}",
        "",
        "## Lưu ý CP3",
        "",
    ]
    if mode == "mock":
        lines += [
            "> Run này dùng **heuristic mock** vì chưa có API key. "
            "Flow + metric đủ để scaffold; **nộp CP3 chính thức cần re-run với GEMINI_API_KEY hoặc OPENAI_API_KEY** "
            "(`LEARNING_ENGINE_MODE=auto`).",
            "",
        ]
    else:
        lines += [
            "> Understanding Estimator gọi **LLM thật** — quyết định trung tâm không hardcode.",
            "",
        ]
        if n_fallback:
            lines += [
                f"> **{n_fallback} case** bị rơi về heuristic fallback do lỗi LLM "
                "(chủ yếu `429 RESOURCE_EXHAUSTED` — quota free tier). "
                "Ghi nhận trung thực; tăng `--sleep` hoặc đổi `GEMINI_MODEL` sang bản flash-lite để chạy lại.",
                "",
            ]

    lines += [
        "## Bảng case",
        "",
        "| id | pass | Q1 | Q2 | Q3 | Q4 | score | band exp/act | move | provider |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        flag = "PASS" if r["pass"] else "FAIL"
        lines.append(
            f"| {r['id']} | {flag} | "
            f"{'Y' if r['q1_band'] else 'N'} | "
            f"{'Y' if r['q2_move'] else 'N'} | "
            f"{'Y' if r['q3_followup'] else 'N'} | "
            f"{'Y' if r['q4_misconception'] else 'N'} | "
            f"{r['score']} | {r['band_expected']}/{r['band_actual']} | "
            f"`{r['move']}` | {r['provider']} |"
        )

    fails = [r for r in rows if not r["pass"]]
    lines += ["", "## Case fail — phân tích", ""]
    if not fails:
        lines.append("Không có case fail.")
    else:
        for r in fails:
            dims = []
            if not r["q1_band"]:
                dims.append(f"Q1 band (exp={r['band_expected']} act={r['band_actual']} score={r['score']})")
            if not r["q2_move"]:
                dims.append("Q2 move")
            if not r["q3_followup"]:
                dims.append("Q3 follow-up")
            if not r["q4_misconception"]:
                dims.append(f"Q4 misconceptions={r['misconceptions']}")
            lines.append(f"- **{r['id']}**: {', '.join(dims)}. Reason: {r['reason']}")

    lines += [
        "",
        "## Phân bố teaching move (output)",
        "",
    ]
    from collections import Counter

    moves = Counter(r["move"] for r in rows)
    for k, v in moves.most_common():
        lines.append(f"- `{k}`: {v}")

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, default=1)
    parser.add_argument(
        "--sleep",
        type=float,
        default=6.0,
        help="Giây nghỉ giữa các case để tránh 429 free tier (0 nếu chạy mock)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Ghi đè GEMINI_MODEL cho lượt đo này (vd. gemini-3.1-flash-lite)",
    )
    args = parser.parse_args()

    if args.model:
        os.environ["GEMINI_MODEL"] = args.model

    cases = load_golden(GOLDEN)
    engine = LearningEngine()
    mode = resolve_mode()
    delay = 0.0 if mode == "mock" else args.sleep

    rows = []
    for i, case in enumerate(cases, 1):
        row = eval_case(engine, case)
        rows.append(row)
        print(f"  [{i}/{len(cases)}] {row['id']} provider={row['provider']} pass={row['pass']}")
        if delay and i < len(cases):
            time.sleep(delay)

    out_md = ROOT / "eval" / f"results-run{args.run}.md"
    out_json = ROOT / "eval" / f"results-run{args.run}.json"
    out_md.write_text(render_md(rows, args.run, mode), encoding="utf-8")
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    n_pass = sum(1 for r in rows if r["pass"])
    print(f"mode={mode} pass={n_pass}/{len(rows)} -> {out_md}")


if __name__ == "__main__":
    main()
