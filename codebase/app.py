"""Streamlit UI — Learning Engine Tutor (CP2/CP3)."""

from __future__ import annotations

import sys
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning_engine.llm_client import resolve_mode  # noqa: E402
from learning_engine.pipeline import LearningEngine  # noqa: E402
from learning_engine.grading import grade_check_answer  # noqa: E402
from learning_engine.followup import CheckQuestion  # noqa: E402
from learning_engine.response import _mcq_block  # noqa: E402
from learning_engine.example import ExampleIllustration  # noqa: E402
from learning_engine.lesson_retriever import list_sessions, retrieve_lesson_context  # noqa: E402
from learning_engine.slide_ingest import (  # noqa: E402
    delete_uploaded_lesson,
    ingest_pdf_slide,
    list_uploaded_sessions,
)


def _fresh_engine() -> LearningEngine:
    """Tạo engine mới — không reload module (reload dễ làm Streamlit lỗi trên UI)."""
    return LearningEngine()


def _example_block_from_dict(ex: dict | None) -> str:
    if not ex:
        return ""
    try:
        obj = ExampleIllustration(
            title=str(ex.get("title") or "Ví dụ"),
            scenario=str(ex.get("scenario") or ""),
            mapping=str(ex.get("mapping") or ""),
            takeaway=str(ex.get("takeaway") or ""),
            provider=str(ex.get("provider") or "template"),
        )
        return obj.markdown()
    except Exception:
        return ""


def _strip_structured_blocks(text: str) -> str:
    """Giữ phần giảng, bỏ ví dụ/MCQ/take-note đã tách ra UI riêng."""
    text = (text or "").strip()
    for marker in ("### Ví dụ minh họa", "### Câu hỏi kiểm tra"):
        if marker in text:
            text = text.split(marker)[0].rstrip()
            if text.endswith("---"):
                text = text[:-3].rstrip()
    # Gỡ dòng take-note markdown nếu còn
    lines = []
    for line in text.splitlines():
        if "Take-note:" in line or "📝" in line:
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _compose_assistant_content(data: dict, raw_response: str) -> str:
    """Nội dung chat đầy đủ (fallback); UI cũng render tách block cho dễ thấy."""
    text = _strip_structured_blocks(raw_response)
    take_note = (data.get("scope_take_note") or "").strip()
    example = data.get("example")
    check = data.get("check_question")
    band = data.get("scope_category") or ""

    parts: list[str] = []
    if band == "related_external" and take_note:
        parts.append(take_note)
    if text:
        parts.append(text)
    if band == "in_lesson" and example:
        block = _example_block_from_dict(example)
        if block:
            parts.append(block)
    if check and check.get("options"):
        try:
            cq = CheckQuestion(
                question=str(check.get("question") or ""),
                options=dict(check.get("options") or {}),
                correct_option=str(check.get("correct_option") or "A"),
                explanation=str(check.get("explanation") or ""),
                intent=str(check.get("intent") or "check"),
            )
            parts.append(_mcq_block(cq))
        except Exception:
            pass
    return "\n\n".join(parts).strip()


def _ensure_mcq_in_content(content: str, check: dict | None) -> str:
    """Backward-compatible wrapper."""
    return _compose_assistant_content(
        {"check_question": check, "scope_category": "in_lesson"},
        content,
    )


def _strategy_label(code: str) -> str:
    return {
        "review_concept": "Ôn lại khái niệm",
        "give_example": "Minh họa bằng ví dụ",
        "validate_understanding": "Kiểm tra hiểu bài",
        "give_hint": "Gợi ý hướng nghĩ",
        "next_topic": "Sang ý tiếp theo",
        "out_of_scope": "Ngoài phạm vi",
    }.get(code or "", code or "—")


def _band_label(band: str) -> str:
    return {
        "in_lesson": "Trong bài học",
        "related_external": "Ngoài bài · hơi liên quan",
        "refuse": "Từ chối",
        "greeting": "Chào hỏi",
        "ambiguous": "Chưa rõ",
    }.get(band or "", band or "—")


def _score_tone(score: int) -> str:
    if score >= 71:
        return "high"
    if score >= 40:
        return "mid"
    return "low"


def _render_mcq(
    check: dict,
    *,
    active: bool,
    last: dict | None,
    widget_key: str,
) -> None:
    """Hiển thị câu trắc nghiệm và cho phép trả lời ngay trong tin nhắn Tutor."""
    opts = check.get("options") or {}
    rows = ""
    if not active:
        rows = "".join(
            f'<div class="mcq-opt"><span class="mcq-key">{escape(k)}</span>'
            f"<span>{escape(str(opts[k]))}</span></div>"
            for k in ("A", "B", "C", "D")
            if k in opts
        )
    hint = (
        "Chọn đáp án và nộp ngay bên dưới câu hỏi."
        if active
        else "Câu hỏi này đã được trả lời hoặc bỏ qua."
    )
    st.markdown(
        f"""
        <div class="mcq-card">
          <div class="mcq-card-label">Câu hỏi kiểm tra</div>
          <div class="mcq-q">{escape(check.get("question") or "")}</div>
          {rows}
          <div class="mcq-hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not active:
        return

    option_labels = [
        f"{key}. {value}" for key, value in sorted(opts.items())
    ]
    choice_label = st.radio(
        "Chọn một đáp án",
        options=option_labels,
        index=None,
        key=widget_key,
    )
    submit_col, skip_col = st.columns([1.2, 1])
    with submit_col:
        submit_mcq = st.button(
            "Nộp đáp án",
            use_container_width=True,
            type="primary",
            key=f"{widget_key}_submit",
        )
    with skip_col:
        skip_mcq = st.button(
            "Bỏ qua",
            use_container_width=True,
            key=f"{widget_key}_skip",
        )

    if submit_mcq and _handle_mcq_submit(check, choice_label, last):
        st.rerun()
    if skip_mcq:
        st.session_state.pending_check = None
        st.session_state.check_feedback = {
            "skipped": True,
            "feedback": "Đã bỏ qua câu trắc nghiệm.",
        }
        st.rerun()

def _handle_mcq_submit(check: dict, choice_label: str | None, last: dict) -> bool:
    """Xử lý nộp MCQ. True nếu đã rerun."""
    if not choice_label:
        st.warning("Hãy chọn một đáp án trước khi nộp.")
        return False
    selected = choice_label.split(".", 1)[0].strip()
    graded = grade_check_answer(
        check,
        selected,
        st.session_state.latest_score
        if st.session_state.latest_score is not None
        else last["understanding_score"],
    )
    st.session_state.latest_score = graded["updated_score"]
    st.session_state.check_feedback = graded
    last["understanding_score"] = graded["updated_score"]
    last["check_result"] = graded
    if graded["is_correct"]:
        last["misconceptions"] = []
        icon, lead = "✅", graded["feedback"]
    else:
        icon, lead = "❌", graded["feedback"]
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": (
                f"{icon} {lead}\n\n"
                f"Mức hiểu bài: **{graded['previous_score']}% → {graded['updated_score']}%**."
                + ("" if graded["is_correct"] else " Bạn có thể hỏi lại phần còn chưa rõ.")
            ),
        }
    )
    st.session_state.pending_check = None
    return True


def _eval_board_html(
    score: int,
    confidence: str,
    strategy: str,
    band: str,
    reason: str,
    misconceptions: list,
    initial_score: int | None = None,
    matrix: dict | None = None,
    matrix_comment: str = "",
) -> str:
    tone = _score_tone(score)
    conf_vi = {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}.get(confidence, confidence)
    misc_html = (
        "<ul class='eval-misc'>"
        + "".join(f"<li>{escape(m)}</li>" for m in misconceptions)
        + "</ul>"
        if misconceptions
        else "<div class='eval-ok'>Chưa phát hiện hiểu lầm cụ thể</div>"
    )
    delta = ""
    if initial_score is not None and initial_score != score:
        delta = (
            f"<div class='eval-delta'>Sau MCQ: {initial_score}% → <b>{score}%</b></div>"
        )

    matrix_html = ""
    m = matrix or {}
    if m:
        axes = [
            ("evidence", "Bằng chứng tự hiểu", int(m.get("evidence") or 0)),
            ("lesson_grounding", "Bám slide / bài", int(m.get("lesson_grounding") or 0)),
            ("authenticity", "Không dán nguyên văn", int(m.get("authenticity") or 0)),
            ("concept_accuracy", "Đúng khái niệm bài", int(m.get("concept_accuracy") or 0)),
        ]
        rows = []
        for key, label, val in axes:
            v = max(0, min(100, val))
            tone_ax = _score_tone(v)
            paste_tag = ""
            if key == "authenticity" and m.get("paste_detected"):
                paste_tag = " <em class='paste-flag'>· dán slide</em>"
            rows.append(
                f"<div class='mx-row'>"
                f"<div class='mx-label'>{escape(label)}{paste_tag}</div>"
                f"<div class='mx-track'><div class='mx-fill score-{tone_ax}' style='width:{v}%'></div></div>"
                f"<div class='mx-val'>{v}</div>"
                f"</div>"
            )
        if matrix_comment:
            comment = escape(matrix_comment)
        elif m.get("notes"):
            comment = escape(str(m["notes"][0]))
        else:
            comment = "—"
        matrix_html = (
            "<div class='eval-matrix'>"
            "<span class='signal-label'>Matrix đánh giá (có ngữ cảnh slide)</span>"
            + "".join(rows)
            + f"<div class='mx-note'>{comment}</div>"
            "</div>"
        )

    return f"""
    <div class="eval-board">
      <div class="eval-top">
        <div class="score-ring score-{tone}">
          <div class="score-num">{score}%</div>
          <div class="score-cap">Mức hiểu</div>
        </div>
        <div class="eval-facts">
          <div class="fact"><span>Độ tin cậy</span><b>{escape(str(conf_vi))}</b></div>
          <div class="fact"><span>Chiến lược</span><b>{escape(_strategy_label(strategy))}</b></div>
          <div class="fact"><span>Phạm vi</span><b>{escape(_band_label(band))}</b></div>
        </div>
      </div>
      <div class="score-bar"><div class="score-fill score-{tone}" style="width:{max(4, min(100, score))}%"></div></div>
      {delta}
      {matrix_html}
      <div class="eval-reason">
        <span class="signal-label">Vì sao đánh giá vậy?</span>
        {escape(reason or "—")}
      </div>
      <div class="eval-misc-wrap">
        <span class="signal-label">Hiểu lầm</span>
        {misc_html}
      </div>
    </div>
    """


st.set_page_config(
    page_title="VLearn · Learning Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');
    :root {
      --ink: #1c1917;
      --muted: #78716c;
      --line: #e7e5e4;
      --paper: #fafaf9;
      --card: #ffffff;
      --teal: #0f766e;
      --teal-soft: #ccfbf1;
      --amber: #b45309;
      --rose: #be123c;
      --sky: #0369a1;
    }
    .stApp {
      font-family: "Source Sans 3", "Segoe UI", sans-serif;
      background:
        radial-gradient(ellipse 70% 40% at 0% -10%, rgba(15,118,110,.10), transparent 55%),
        radial-gradient(ellipse 50% 35% at 100% 0%, rgba(180,83,9,.07), transparent 50%),
        linear-gradient(180deg, #f5f5f4 0%, #fafaf9 40%, #f5f5f4 100%);
      color: var(--ink);
    }
    .block-container { max-width: 1280px; padding-top: 1.1rem; padding-bottom: 2rem; }
    h1,h2,h3, .brand-title, .section-heading {
      font-family: "Fraunces", Georgia, serif !important;
      letter-spacing: -.01em;
    }

    .hero {
      display: flex; align-items: center; justify-content: space-between; gap: 1rem;
      padding: 1rem 1.25rem; margin-bottom: .75rem;
      background: rgba(255,255,255,.82);
      border: 1px solid var(--line); border-radius: 18px;
      box-shadow: 0 10px 30px rgba(28,25,23,.04);
    }
    .brand { display: flex; align-items: center; gap: .85rem; }
    .brand-icon {
      width: 46px; height: 46px; border-radius: 14px;
      display: grid; place-items: center;
      background: linear-gradient(145deg, #0f766e, #115e59);
      color: #ecfdf5; font-size: 1.25rem;
    }
    .brand-title { font-size: 1.35rem; font-weight: 700; color: #1c1917; }
    .brand-subtitle { margin-top: .12rem; color: var(--muted); font-size: .9rem; }
    .provider-pill {
      padding: .42rem .72rem; border-radius: 999px; font-size: .78rem; font-weight: 650;
      background: var(--teal-soft); color: var(--teal); border: 1px solid #99f6e4;
    }
    .provider-pill.mock { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }

    .section-heading {
      display: flex; align-items: center; gap: .5rem;
      margin: .2rem 0 .7rem; color: #1c1917; font-size: 1.05rem; font-weight: 700;
    }
    .section-heading span {
      width: 28px; height: 28px; border-radius: 9px; display: grid; place-items: center;
      background: #f5f5f4; font-size: .9rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
      background: rgba(255,255,255,.92) !important;
      border-color: var(--line) !important; border-radius: 16px !important;
      box-shadow: 0 6px 22px rgba(28,25,23,.04);
    }
    [data-testid="stChatMessage"] {
      border-radius: 14px; padding: .55rem .65rem; margin-bottom: .4rem;
      border: 1px solid transparent;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
      background: #f0fdfa; border-color: #ccfbf1;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
      background: #fff; border-color: var(--line);
    }
    [data-testid="stChatInput"] {
      border: 1px solid #d6d3d1; border-radius: 14px;
      box-shadow: 0 4px 16px rgba(28,25,23,.05);
    }
    [data-testid="stChatInput"]:focus-within {
      border-color: #14b8a6; box-shadow: 0 0 0 3px rgba(20,184,166,.15);
    }

    .topic-chip-row { display: flex; flex-wrap: wrap; gap: .4rem; margin: .35rem 0 .65rem; }
    .topic-chip {
      padding: .28rem .55rem; border-radius: 999px; font-size: .78rem; font-weight: 600;
      background: #f5f5f4; color: #44403c; border: 1px solid var(--line);
    }

    .note-card, .example-card, .mcq-card {
      margin: .55rem 0; padding: .85rem 1rem; border-radius: 14px; font-size: .92rem;
    }
    .note-card {
      background: #fffbeb; border: 1px solid #fde68a; color: #78350f;
    }
    .example-card {
      background: #f0fdfa; border: 1px solid #99f6e4; color: #134e4a;
    }
    .example-card b { color: #0f766e; }
    .mcq-card {
      background: #f8fafc; border: 1px solid #cbd5e1;
    }
    .mcq-card-label, .signal-label {
      display: block; margin-bottom: .3rem;
      font-size: .7rem; font-weight: 700; letter-spacing: .05em;
      text-transform: uppercase; color: #78716c;
    }
    .mcq-q { font-weight: 650; color: #1c1917; margin-bottom: .55rem; line-height: 1.4; }
    .mcq-opt {
      display: flex; gap: .55rem; align-items: flex-start;
      padding: .45rem .55rem; margin: .28rem 0;
      background: #fff; border: 1px solid var(--line); border-radius: 10px;
      color: #44403c; font-size: .9rem;
    }
    .mcq-key {
      flex: none; width: 1.55rem; height: 1.55rem; border-radius: 7px;
      display: grid; place-items: center;
      background: #0f766e; color: #fff; font-size: .75rem; font-weight: 700;
    }
    .mcq-hint { margin-top: .55rem; color: var(--muted); font-size: .8rem; }

    .quiz-dock {
      margin-top: .65rem; padding: 1rem 1.05rem;
      border-radius: 16px; border: 1px solid #99f6e4;
      background: linear-gradient(180deg, #f0fdfa, #fff);
      box-shadow: 0 8px 24px rgba(15,118,110,.08);
    }
    .quiz-dock h4 {
      margin: 0 0 .35rem; font-family: Fraunces, Georgia, serif;
      color: #0f766e; font-size: 1.05rem;
    }

    .eval-board {
      padding: 1rem; border-radius: 16px; border: 1px solid var(--line);
      background: var(--card); box-shadow: 0 8px 24px rgba(28,25,23,.04);
    }
    .eval-top { display: flex; gap: .9rem; align-items: center; margin-bottom: .7rem; }
    .score-ring {
      width: 88px; height: 88px; border-radius: 50%;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      border: 4px solid #d6d3d1; background: #fafaf9;
    }
    .score-ring.score-high { border-color: #14b8a6; background: #f0fdfa; }
    .score-ring.score-mid { border-color: #f59e0b; background: #fffbeb; }
    .score-ring.score-low { border-color: #f43f5e; background: #fff1f2; }
    .score-num { font-family: Fraunces, Georgia, serif; font-size: 1.35rem; font-weight: 700; line-height: 1; }
    .score-cap { font-size: .65rem; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; margin-top: .15rem; }
    .eval-facts { flex: 1; display: flex; flex-direction: column; gap: .35rem; }
    .fact { display: flex; justify-content: space-between; gap: .5rem; font-size: .86rem; color: var(--muted); }
    .fact b { color: #1c1917; font-weight: 650; text-align: right; }
    .score-bar { height: 8px; border-radius: 99px; background: #e7e5e4; overflow: hidden; margin-bottom: .55rem; }
    .score-fill { height: 100%; border-radius: 99px; }
    .score-fill.score-high { background: #14b8a6; }
    .score-fill.score-mid { background: #f59e0b; }
    .score-fill.score-low { background: #f43f5e; }
    .eval-delta { font-size: .82rem; color: var(--teal); margin-bottom: .45rem; }
    .eval-reason, .eval-misc-wrap {
      padding: .65rem .7rem; margin-top: .4rem; border-radius: 12px;
      background: #fafaf9; border: 1px solid var(--line); color: #44403c; font-size: .88rem;
    }
    .eval-matrix {
      margin-top: .7rem; padding: .55rem .65rem .45rem;
      background: #f0fdfa; border: 1px solid #99f6e4; border-radius: 10px;
    }
    .mx-row {
      display: grid; grid-template-columns: 1.35fr 1.6fr 36px;
      gap: .4rem; align-items: center; margin: .28rem 0;
      font-size: .78rem; color: var(--ink);
    }
    .mx-label { color: var(--muted); }
    .mx-track {
      height: 7px; background: #e7e5e4; border-radius: 99px; overflow: hidden;
    }
    .mx-fill { height: 100%; border-radius: 99px; }
    .mx-fill.score-high { background: var(--teal); }
    .mx-fill.score-mid { background: var(--amber); }
    .mx-fill.score-low { background: var(--rose); }
    .mx-val { text-align: right; font-weight: 700; font-size: .78rem; }
    .mx-note { margin-top: .35rem; font-size: .78rem; color: var(--muted); line-height: 1.35; }
    .paste-flag { color: var(--rose); font-style: normal; font-weight: 600; }
    .eval-ok { color: var(--teal); font-weight: 600; font-size: .88rem; }
    .eval-misc { margin: .2rem 0 0; padding-left: 1.1rem; color: var(--rose); }
    .signal-card {
      padding: .75rem .85rem; margin: .4rem 0; border: 1px solid var(--line);
      border-radius: 12px; background: #fafaf9; color: #57534e; font-size: .88rem;
    }
    .tag {
      display: inline-block; padding: .18rem .48rem; border-radius: 7px;
      background: #ccfbf1; color: #0f766e; font-size: .78rem; font-weight: 650;
    }
    .empty-chat {
      min-height: 360px; display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center; color: var(--muted);
    }
    .empty-icon {
      width: 56px; height: 56px; margin-bottom: .7rem; border-radius: 16px;
      display: grid; place-items: center; background: #f0fdfa; font-size: 1.5rem;
    }
    .empty-title { color: #292524; font-family: Fraunces, Georgia, serif; font-weight: 700; margin-bottom: .25rem; }
    .empty-copy { font-size: .86rem; max-width: 320px; }

    .turn-table { width: 100%; border-collapse: collapse; font-size: .8rem; margin-top: .35rem; }
    .turn-table th, .turn-table td {
      padding: .4rem .35rem; border-bottom: 1px solid var(--line); text-align: left;
    }
    .turn-table th { color: var(--muted); font-weight: 650; font-size: .7rem; text-transform: uppercase; }
    .pill-mini {
      display: inline-block; padding: .1rem .35rem; border-radius: 6px;
      background: #f5f5f4; color: #44403c; font-size: .72rem; font-weight: 600;
    }


    .stButton > button {
      border-radius: 11px; border-color: #d6d3d1; color: #44403c; font-weight: 600;
    }
    .stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {
      background: #0f766e; border-color: #0f766e; color: #fff;
    }
    .stButton > button:hover { border-color: #0f766e; color: #0f766e; background: #f0fdfa; }
    [data-testid="stMetric"] {
      background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: .55rem .7rem;
    }
    [data-testid="stMetricValue"] { color: #0f766e; }
    hr { border-color: var(--line) !important; }
    @media (max-width: 760px) {
      .hero { align-items: flex-start; }
      .provider-pill { display: none; }
      .eval-top { flex-direction: column; align-items: flex-start; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

mode = resolve_mode()
provider_class = "mock" if mode == "mock" else ""
provider_text = "Chế độ demo" if mode == "mock" else f"{mode.title()} · Online"
st.markdown(
    f"""
    <div class="hero">
      <div class="brand">
        <div class="brand-icon">V</div>
        <div>
          <div class="brand-title">VLearn Learning Tutor</div>
          <div class="brand-subtitle">
            Hỏi khái niệm · xem ví dụ · làm câu kiểm tra · theo dõi mức hiểu
          </div>
        </div>
      </div>
      <div class="provider-pill {provider_class}">●&nbsp; {provider_text}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
if mode == "mock":
    st.warning("Chưa kết nối AI thật. Thêm API key vào `codebase/.env` để bật Gemini.")

if "engine" not in st.session_state:
    st.session_state.engine = LearningEngine()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "turn_logs" not in st.session_state:
    st.session_state.turn_logs = []
if "pending_check" not in st.session_state:
    st.session_state.pending_check = None
if "latest_score" not in st.session_state:
    st.session_state.latest_score = None
if "check_feedback" not in st.session_state:
    st.session_state.check_feedback = None

col_chat, col_side = st.columns([1.65, 1], gap="large")

# ---------------------------------------------------------------------------
# Cột trái — Chat + trả lời MCQ
# ---------------------------------------------------------------------------
with col_chat:
    st.markdown(
        '<div class="section-heading"><span>💬</span> Không gian học tập</div>',
        unsafe_allow_html=True,
    )
    topic_hint = st.text_input(
        "Ngữ cảnh khái niệm (tuỳ chọn)",
        value=st.session_state.get("topic_hint", ""),
        placeholder="Ví dụ: Context window · Transformer · Problem Statement",
        help="Bổ sung từ khoá; hệ thống sẽ retrieve đoạn transcript/slide liên quan.",
        key="topic_hint",
    )

    with st.expander("📥 Nhập slide PDF → thêm vào danh sách buổi học", expanded=False):
        st.caption(
            "Upload PDF slide (có chữ). Hệ thống trích text theo trang, lưu thành buổi học "
            "để chọn bên dưới. PDF scan ảnh thuần có thể không đọc được."
        )
        up_name = st.text_input(
            "Tên buổi học (tuỳ chọn)",
            placeholder="VD: Day 3 — Prompting & Agent",
            key="pdf_lesson_label",
        )
        uploaded = st.file_uploader(
            "Chọn file PDF",
            type=["pdf"],
            key="pdf_slide_uploader",
            accept_multiple_files=False,
        )
        u1, u2 = st.columns(2)
        with u1:
            do_ingest = st.button("Học từ PDF & thêm buổi", use_container_width=True, type="primary")
        with u2:
            refresh_list = st.button("Làm mới danh sách", use_container_width=True)

        if refresh_list:
            st.rerun()

        if do_ingest:
            if not uploaded:
                st.warning("Hãy chọn một file PDF trước.")
            else:
                try:
                    meta = ingest_pdf_slide(
                        filename=uploaded.name,
                        data=uploaded.getvalue(),
                        label=up_name.strip(),
                    )
                    # Option unique trong dropdown (label + đuôi id)
                    st.session_state["lesson_session_label"] = (
                        f"{meta['label']}  ·  {meta['id'][-6:]}"
                    )
                    st.success(
                        f"Đã thêm buổi «{meta['label']}» "
                        f"({meta.get('page_count', '?')} trang). "
                        "Chọn bài học ở khung bên dưới để tutor dùng context slide này."
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Không ingest được PDF: {exc}")

        uploaded_sessions = list_uploaded_sessions()
        if uploaded_sessions:
            st.caption(f"Đã học {len(uploaded_sessions)} slide PDF trên máy này.")
            del_options = ["(không xoá)"] + [
                f"{s['label']}  ·  {s['id'][-6:]}" for s in uploaded_sessions
            ]
            del_choice = st.selectbox(
                "Xoá buổi PDF (tuỳ chọn)",
                options=del_options,
                key="pdf_delete_label",
            )
            if st.button("Xoá buổi PDF đã chọn") and del_choice != "(không xoá)":
                lid = next(
                    (
                        s["id"]
                        for s in uploaded_sessions
                        if f"{s['label']}  ·  {s['id'][-6:]}" == del_choice
                    ),
                    "",
                )
                if lid and delete_uploaded_lesson(lid):
                    st.success(f"Đã xoá {del_choice}")
                    st.rerun()

    # --- Chọn bài học từ context đã học ---
    from learning_engine.lesson_retriever import clear_lesson_cache

    clear_lesson_cache()
    uploaded_now = list_uploaded_sessions()
    catalog = list_sessions()
    # PDF: lấy trực tiếp từ index (không phụ thuộc cache list_sessions)
    learned_pdf = []
    for s in uploaded_now:
        item = dict(s)
        item["display"] = f"{item['label']}  ·  {item['id'][-6:]}"
        learned_pdf.append(item)
    built_in = [s for s in catalog if s.get("source") != "pdf"]

    session_labels = ["(Tự chọn theo câu hỏi)"]
    id_by_label: dict[str, str] = {}
    for s in learned_pdf:
        disp = s["display"]
        session_labels.append(disp)
        id_by_label[disp] = s["id"]
    for s in built_in:
        disp = s.get("display") or s["label"]
        session_labels.append(disp)
        id_by_label[disp] = s["id"]

    cur_label = st.session_state.get("lesson_session_label")
    if cur_label not in session_labels:
        mapped = next(
            (
                s["display"]
                for s in learned_pdf
                if s.get("label") == cur_label
                or str(cur_label or "").startswith(str(s.get("label") or "___"))
            ),
            None,
        )
        st.session_state["lesson_session_label"] = mapped or session_labels[0]

    # Đổi key khi số PDF đổi → Streamlit không giữ options cũ
    select_key = f"lesson_session_label_v2_{len(learned_pdf)}_{uploaded_now[0]['id'][-6:] if uploaded_now else 'none'}"
    # Đồng bộ giá trị sang key động
    if select_key not in st.session_state:
        st.session_state[select_key] = st.session_state.get(
            "lesson_session_label", session_labels[0]
        )
        if st.session_state[select_key] not in session_labels:
            st.session_state[select_key] = session_labels[0]

    with st.container(border=True):
        st.markdown("**Chọn bài học (context slide đã học)**")
        if learned_pdf:
            st.success(
                f"Có **{len(learned_pdf)}** slide PDF đã học — chọn ở dưới "
                f"(vd. `{learned_pdf[0]['display']}`)."
            )
            # Nút chọn nhanh từng PDF (không phụ thuộc selectbox cũ)
            cols = st.columns(min(3, len(learned_pdf)))
            for i, s in enumerate(learned_pdf[:6]):
                with cols[i % len(cols)]:
                    if st.button(
                        s["display"],
                        key=f"pick_pdf_{s['id']}",
                        use_container_width=True,
                    ):
                        st.session_state["lesson_session_label"] = s["display"]
                        st.session_state[select_key] = s["display"]
                        st.rerun()
        else:
            st.warning("Chưa có slide PDF nào. Upload ở khung trên rồi bấm «Học từ PDF».")

        st.caption("Hoặc chọn trong danh sách đầy đủ (PDF + transcript):")
        session_choice = st.selectbox(
            "Bài học / slide nguồn",
            options=session_labels,
            help="Slide PDF đã học nằm đầu danh sách.",
            key=select_key,
            label_visibility="collapsed",
        )
        st.session_state["lesson_session_label"] = session_choice
        session_id = id_by_label.get(session_choice, "")

        if session_id:
            preview = retrieve_lesson_context(
                student_message=topic_hint.strip() or session_choice,
                topic_hint=topic_hint.strip(),
                session_id=session_id,
                top_k=3,
            )
            src_tag = "PDF đã học" if session_id.startswith("pdf_") else "Transcript khoá"
            heads = preview.headings[:4] or ["(đang nạp mục…)"]
            st.markdown(
                f"""
                <div class="signal-card">
                  <span class="signal-label">Context đang dùng · {escape(src_tag)}</span>
                  <b>{escape(preview.session_label or session_choice)}</b><br/>
                  <span style="color:#78716c;font-size:.82rem">
                    Mục: {escape(" · ".join(heads))}
                  </span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.caption("Chưa chọn buổi — hệ thống sẽ tự khớp theo câu hỏi.")

    slide_paste = ""
    st.markdown(
        """
        <div class="topic-chip-row">
          <span class="topic-chip">Upload PDF → chọn bài học</span>
          <span class="topic-chip">context từ slide đã học</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    check = st.session_state.pending_check
    last = st.session_state.turn_logs[-1] if st.session_state.turn_logs else None
    already_graded = bool(last and last.get("check_result"))

    with st.container(height=460, border=True):
        if not st.session_state.messages:
            st.markdown(
                """
                <div class="empty-chat">
                  <div class="empty-icon">✦</div>
                  <div class="empty-title">Bắt đầu bằng một khái niệm trên slide</div>
                  <div class="empty-copy">
                    Tutor sẽ giải thích, đưa ví dụ (nếu trong bài), rồi hỏi một câu trắc nghiệm
                    để cập nhật mức hiểu của bạn.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        for message_index, msg in enumerate(st.session_state.messages):
            avatar = "🧑‍🎓" if msg["role"] == "student" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                if msg["role"] == "assistant" and msg.get("meta"):
                    m = msg["meta"]
                    band = m.get("scope_category", "in_lesson")
                    if band == "related_external" and m.get("scope_take_note"):
                        note = m["scope_take_note"].replace("📝 **Take-note:** ", "")
                        st.markdown(
                            f'<div class="note-card"><span class="signal-label">Take-note</span>{escape(note)}</div>',
                            unsafe_allow_html=True,
                        )
                    body = _strip_structured_blocks(msg.get("content") or "")
                    if body:
                        st.markdown(body)
                    if band == "in_lesson" and m.get("example"):
                        ex = m["example"]
                        st.markdown(
                            f"""
                            <div class="example-card">
                              <span class="signal-label">Ví dụ minh họa · trong bài</span>
                              <b>{escape(ex.get("title", ""))}</b><br/><br/>
                              {escape(ex.get("scenario", ""))}<br/><br/>
                              <i>Ánh xạ:</i> {escape(ex.get("mapping", ""))}<br/>
                              <i>Ý nhớ:</i> {escape(ex.get("takeaway", ""))}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    cq = m.get("check_question") or {}
                    if cq.get("options"):
                        active_check = bool(
                            check
                            and cq == check
                            and last
                            and message_index == len(st.session_state.messages) - 1
                            and not already_graded
                        )
                        _render_mcq(
                            cq,
                            active=active_check,
                            last=last,
                            widget_key=f"mcq_radio_chat_{message_index}",
                        )
                    score_show = m.get("understanding_score", "?")
                    st.caption(
                        f"{_band_label(band)} · hiểu {score_show}% · "
                        f"{_strategy_label(m.get('teaching_strategy', ''))}"
                    )
                else:
                    st.markdown(msg["content"])

        live_user_message = st.empty()

    if st.session_state.check_feedback and not st.session_state.check_feedback.get("skipped"):
        fb = st.session_state.check_feedback
        if fb.get("is_correct"):
            st.success(f"Đúng · hiểu bài {fb['previous_score']}% → {fb['updated_score']}%")
        elif "is_correct" in fb:
            st.warning(f"Chưa đúng · hiểu bài {fb['previous_score']}% → {fb['updated_score']}%")

    prompt = st.chat_input("Hỏi khái niệm hoặc diễn đạt lại điều bạn vừa hiểu…")
    if prompt:
        st.session_state.messages.append({"role": "student", "content": prompt})
        with live_user_message.container():
            with st.chat_message("user", avatar="🧑‍🎓"):
                st.markdown(prompt)
        history = [
            {"role": "student" if m["role"] == "student" else "tutor", "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]
        st.session_state.engine = _fresh_engine()
        with st.spinner("Tutor đang chuẩn bị giải thích và câu kiểm tra…"):
            try:
                result = st.session_state.engine.run(
                    prompt,
                    history=history,
                    topic_hint=topic_hint.strip(),
                    session_id=session_id,
                    slide_paste=(slide_paste or "").strip(),
                )
            except Exception as exc:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": (
                            "Xin lỗi, lượt này chưa xử lý được. "
                            "Bạn thử hỏi lại hoặc kiểm tra kết nối API / quota.\n\n"
                            f"_({type(exc).__name__})_"
                        ),
                    }
                )
                st.session_state.check_feedback = None
                st.rerun()
            else:
                data = result.to_dict()
                content = _compose_assistant_content(data, result.tutor_response)
                st.session_state.turn_logs.append(data)
                st.session_state.latest_score = (
                    None if data.get("api_calls_skipped") else data["understanding_score"]
                )
                st.session_state.pending_check = (
                    None if data.get("api_calls_skipped") else data.get("check_question")
                )
                st.session_state.check_feedback = None
                st.session_state.messages.append(
                    {"role": "assistant", "content": content, "meta": data}
                )
                st.rerun()

# ---------------------------------------------------------------------------
# Cột phải — Bảng đánh giá
# ---------------------------------------------------------------------------
with col_side:
    st.markdown(
        '<div class="section-heading"><span>📊</span> Bảng đánh giá</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.turn_logs:
        last = st.session_state.turn_logs[-1]
        if last.get("api_calls_skipped") or last.get("scope_category") in (
            "refuse",
            "greeting",
            "ambiguous",
        ):
            st.warning("Ngoài phạm vi — chưa có điểm hiểu bài cho lượt này.")
            st.markdown(
                f"""
                <div class="signal-card">
                  <span class="signal-label">Phạm vi · {escape(last.get("scope_category", ""))}</span>
                  {escape(last.get("scope_reason") or "Ngoài phạm vi")}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            shown_score = (
                st.session_state.latest_score
                if st.session_state.latest_score is not None
                else last["understanding_score"]
            )
            pre_mcq = None
            if last.get("check_result"):
                pre_mcq = last["check_result"].get("previous_score")
            st.markdown(
                _eval_board_html(
                    int(shown_score or 0),
                    last.get("confidence", "medium"),
                    last.get("teaching_strategy", ""),
                    last.get("scope_category", "in_lesson"),
                    last.get("understanding_reason", ""),
                    list(last.get("misconceptions") or []),
                    initial_score=pre_mcq,
                    matrix=last.get("understanding_matrix") or {},
                    matrix_comment=str(last.get("matrix_comment") or ""),
                ),
                unsafe_allow_html=True,
            )

            if last.get("lesson_excerpt_preview"):
                heads = " · ".join(last.get("lesson_headings") or [])
                st.markdown(
                    f"""
                    <div class="signal-card">
                      <span class="signal-label">Ngữ cảnh bài học đã đọc</span>
                      <b>{escape(last.get("lesson_session") or "Transcript")}</b><br/>
                      <span style="color:#78716c;font-size:.8rem">{escape(heads)}</span><br/><br/>
                      {escape(last.get("lesson_excerpt_preview") or "")}<br/>
                      <span style="color:#78716c;font-size:.78rem">
                        overlap dán slide: {last.get("lesson_overlap_ratio", 0)}
                        · nguồn: {escape(", ".join(last.get("lesson_sources") or []) or "—")}
                      </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            ex = last.get("example")
            if ex and last.get("scope_category") == "in_lesson":
                st.markdown(
                    f"""
                    <div class="signal-card">
                      <span class="signal-label">Ví dụ đang dùng</span>
                      <b>{escape(ex.get("title", ""))}</b><br/>
                      {escape(ex.get("takeaway", ""))}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            pending = st.session_state.pending_check
            if pending and pending.get("options") and not last.get("check_result"):
                st.info("Có câu kiểm tra đang chờ — chọn đáp án ngay trong tin nhắn của Tutor.")
    else:
        st.markdown(
            """
            <div class="signal-card">
              <span class="signal-label">Chưa có dữ liệu</span>
              Sau câu hỏi đầu tiên, bảng này hiện mức hiểu, chiến lược dạy,
              hiểu lầm và lịch sử các lượt.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="section-heading"><span>📈</span> Tiến trình buổi</div>',
        unsafe_allow_html=True,
    )
    logs = st.session_state.turn_logs
    if logs:
        scores = []
        for t in logs:
            if t.get("api_calls_skipped"):
                continue
            if t.get("check_result"):
                scores.append(t["check_result"].get("updated_score", t["understanding_score"]))
            else:
                scores.append(t["understanding_score"])
        if scores:
            st.caption("Mức hiểu qua từng lượt học")
            st.line_chart({"Mức hiểu (%)": scores}, height=150)

        # Bảng tóm tắt các lượt
        rows_html = []
        for i, t in enumerate(logs, 1):
            sc = "—"
            if not t.get("api_calls_skipped"):
                sc = str(
                    t.get("check_result", {}).get("updated_score", t.get("understanding_score", "—"))
                )
            mcq = "✓" if t.get("check_result") else ("…" if t.get("asked_check_question") else "—")
            rows_html.append(
                "<tr>"
                f"<td>{i}</td>"
                f"<td><b>{escape(str(sc))}</b></td>"
                f"<td><span class='pill-mini'>{escape(_strategy_label(t.get('teaching_strategy','')))}</span></td>"
                f"<td>{escape(_band_label(t.get('scope_category','')))}</td>"
                f"<td>{mcq}</td>"
                "</tr>"
            )
        st.markdown(
            f"""
            <table class="turn-table">
              <thead>
                <tr><th>#</th><th>Hiểu</th><th>Chiến lược</th><th>Phạm vi</th><th>MCQ</th></tr>
              </thead>
              <tbody>{''.join(rows_html)}</tbody>
            </table>
            """,
            unsafe_allow_html=True,
        )
        misc_n = sum(len(t.get("misconceptions") or []) for t in logs)
        check_n = sum(1 for t in logs if t.get("asked_check_question"))
        k1, k2 = st.columns(2)
        k1.metric("Hiểu lầm", misc_n)
        k2.metric("Lượt kiểm tra", f"{check_n}/{len(logs)}")
    else:
        st.caption("Biểu đồ và bảng lượt sẽ xuất hiện khi bạn bắt đầu hỏi.")

st.divider()
footer_left, footer_right = st.columns([3, 1])
with footer_left:
    with st.expander("VLearn Tutor có thể hỗ trợ gì?"):
        st.markdown(
            """
            - Chọn **buổi học** (hoặc dán excerpt slide) để tutor đọc ngữ cảnh bài.
            - Hỏi trong chat · xem **ví dụ** (trong bài) / **take-note** (ngoài bài).
            - Trả lời **câu kiểm tra** để cập nhật mức hiểu trên bảng đánh giá.
            - Không phải điểm số chính thức của khoá.
            """
        )
with footer_right:
    if st.button("↻  Bắt đầu lại", use_container_width=True):
        st.session_state.messages = []
        st.session_state.turn_logs = []
        st.session_state.pending_check = None
        st.session_state.latest_score = None
        st.session_state.check_feedback = None
        st.rerun()
