"""Streamlit UI — Learning Engine Tutor (CP2/CP3)."""

from __future__ import annotations

import sys
from collections import Counter
from html import escape
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning_engine.llm_client import resolve_mode  # noqa: E402
from learning_engine.pipeline import LearningEngine  # noqa: E402
from learning_engine.flow_lab import cache_stats, run_flow_lab  # noqa: E402

st.set_page_config(
    page_title="VLearn · Learning Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    /* Nền và typography */
    .stApp {
        background:
            radial-gradient(circle at 4% 0%, rgba(219, 234, 254, .72), transparent 25rem),
            radial-gradient(circle at 96% 5%, rgba(204, 251, 241, .55), transparent 24rem),
            #f8fafc;
        color: #172033;
    }
    .block-container {
        max-width: 1380px;
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }
    h1, h2, h3 { color: #14213d !important; letter-spacing: -.02em; }

    /* Hero */
    .hero {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.15rem 1.35rem;
        margin-bottom: .85rem;
        background: rgba(255, 255, 255, .88);
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        box-shadow: 0 12px 35px rgba(15, 23, 42, .06);
        backdrop-filter: blur(10px);
    }
    .brand { display: flex; align-items: center; gap: .9rem; }
    .brand-icon {
        display: grid; place-items: center;
        width: 48px; height: 48px;
        border-radius: 15px;
        background: linear-gradient(145deg, #2563eb, #4f46e5);
        color: white; font-size: 1.45rem;
        box-shadow: 0 8px 20px rgba(37, 99, 235, .24);
    }
    .brand-title { font-size: 1.28rem; font-weight: 750; color: #172554; }
    .brand-subtitle { margin-top: .15rem; color: #64748b; font-size: .9rem; }
    .provider-pill {
        flex: none; padding: .48rem .78rem; border-radius: 999px;
        font-size: .8rem; font-weight: 650;
        background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0;
    }
    .provider-pill.mock { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }

    /* Tiêu đề section */
    .section-heading {
        display: flex; align-items: center; gap: .55rem;
        margin: .35rem 0 .65rem;
        color: #1e293b; font-size: 1rem; font-weight: 720;
    }
    .section-heading span {
        display: grid; place-items: center; width: 30px; height: 30px;
        border-radius: 10px; background: #eff6ff;
    }

    /* Cards và chat */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255,255,255,.9);
        border-color: #e2e8f0 !important;
        border-radius: 18px !important;
        box-shadow: 0 8px 28px rgba(15,23,42,.045);
    }
    [data-testid="stChatMessage"] {
        border-radius: 16px;
        padding: .7rem .85rem;
        margin-bottom: .55rem;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: #eff6ff;
        border: 1px solid #dbeafe;
    }
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
    }
    [data-testid="stChatInput"] {
        border: 1px solid #cbd5e1;
        border-radius: 15px;
        box-shadow: 0 5px 18px rgba(15, 23, 42, .06);
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: #60a5fa;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, .16);
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: .7rem .85rem;
    }
    [data-testid="stMetricValue"] { color: #1d4ed8; }
    .signal-card {
        padding: .8rem .9rem; margin: .45rem 0;
        border: 1px solid #e2e8f0; border-radius: 13px;
        background: #f8fafc; color: #475569; font-size: .9rem;
    }
    .signal-label {
        display: block; margin-bottom: .22rem;
        color: #64748b; font-size: .72rem; font-weight: 700;
        letter-spacing: .06em; text-transform: uppercase;
    }
    .tag {
        display: inline-block; padding: .2rem .5rem; border-radius: 7px;
        background: #eef2ff; color: #4338ca; font-size: .78rem; font-weight: 650;
    }
    .empty-chat {
        min-height: 400px; display: flex; flex-direction: column;
        align-items: center; justify-content: center; text-align: center;
        color: #64748b;
    }
    .empty-icon {
        display: grid; place-items: center; width: 58px; height: 58px;
        margin-bottom: .8rem; border-radius: 18px;
        background: #eff6ff; font-size: 1.65rem;
    }
    .empty-title { color: #334155; font-weight: 700; margin-bottom: .25rem; }
    .empty-copy { font-size: .86rem; max-width: 300px; }

    /* Flow Lab */
    .flow-banner {
        padding: .9rem 1rem; margin: .4rem 0 1rem;
        border-radius: 14px; border: 1px solid #dbeafe;
        background: linear-gradient(180deg, #eff6ff, #f8fbff);
        color: #1e3a8a; font-size: .9rem;
    }
    .flow-step {
        padding: .75rem .9rem; margin: .45rem 0;
        border: 1px solid #e2e8f0; border-radius: 12px;
        background: #fff;
    }
    .flow-step-title {
        display: flex; align-items: center; justify-content: space-between;
        gap: .5rem; margin-bottom: .28rem;
        color: #0f172a; font-weight: 700; font-size: .92rem;
    }
    .src-pill {
        display: inline-block; padding: .15rem .48rem; border-radius: 999px;
        font-size: .72rem; font-weight: 700; text-transform: uppercase;
        letter-spacing: .04em;
    }
    .src-cache { background: #ecfdf5; color: #047857; }
    .src-golden_set { background: #eff6ff; color: #1d4ed8; }
    .src-api { background: #fff7ed; color: #c2410c; }
    .src-rule, .src-local, .src-template {
        background: #f1f5f9; color: #475569;
    }
    .flow-step-detail { color: #64748b; font-size: .86rem; }

    /* Buttons */
    .stButton > button {
        border-radius: 11px; border-color: #cbd5e1;
        color: #334155; font-weight: 600;
    }
    .stButton > button:hover {
        border-color: #3b82f6; color: #1d4ed8; background: #eff6ff;
    }
    hr { border-color: #e2e8f0 !important; }
    @media (max-width: 760px) {
        .hero { align-items: flex-start; }
        .provider-pill { display: none; }
        .block-container { padding: .8rem; }
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
        <div class="brand-icon">✦</div>
        <div>
          <div class="brand-title">VLearn Learning Tutor</div>
          <div class="brand-subtitle">
            Hiểu bạn đang học đến đâu · Chọn cách hướng dẫn phù hợp
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

col_chat, col_side = st.columns([1.55, 1], gap="large")

with col_side:
    st.markdown(
        '<div class="section-heading"><span>🧭</span> Phân tích lượt học</div>',
        unsafe_allow_html=True,
    )
    if st.session_state.turn_logs:
        last = st.session_state.turn_logs[-1]
        metric_col, confidence_col = st.columns(2)
        with metric_col:
            st.metric("Mức độ hiểu", f"{last['understanding_score']}%")
        with confidence_col:
            confidence_labels = {"low": "Thấp", "medium": "Trung bình", "high": "Cao"}
            st.metric("Độ tin cậy", confidence_labels.get(last["confidence"], last["confidence"]))

        st.markdown(
            f"""
            <div class="signal-card">
              <span class="signal-label">Vì sao hệ thống đánh giá như vậy?</span>
              {escape(last["understanding_reason"])}
            </div>
            <div class="signal-card">
              <span class="signal-label">Chiến lược hướng dẫn</span>
              <span class="tag">{escape(last["teaching_strategy"])}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        misconceptions = last["misconceptions"]
        if misconceptions:
            st.error("Hiểu lầm cần điều chỉnh: " + " · ".join(misconceptions))
        else:
            st.success("Chưa phát hiện hiểu lầm cụ thể.")

        followup = last["follow_ups"][0] if last["follow_ups"] else "Chưa có gợi ý tiếp theo."
        follow_src = last.get("provider_followup", "template")
        st.markdown(
            f"""
            <div class="signal-card">
              <span class="signal-label">Câu hỏi tiếp theo · {escape(follow_src)}</span>
              {escape(followup)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Bỏ qua gợi ý", use_container_width=True):
            st.info("Bạn có thể tiếp tục đặt bất kỳ câu hỏi nào trong khung chat.")
    else:
        with st.container(border=True):
            st.markdown(
                "Hệ thống sẽ hiển thị **mức độ hiểu**, **chiến lược dạy** "
                "và **gợi ý tiếp theo** sau câu hỏi đầu tiên."
            )

    st.markdown(
        '<div class="section-heading"><span>📈</span> Tiến trình buổi học</div>',
        unsafe_allow_html=True,
    )
    logs = st.session_state.turn_logs
    if logs:
        scores = [t["understanding_score"] for t in logs]
        st.caption("Mức độ hiểu qua từng lượt")
        st.line_chart({"Mức độ hiểu": scores}, height=170)
        moves = Counter(t["teaching_strategy"] for t in logs)
        st.caption("Phân bố chiến lược hướng dẫn")
        st.bar_chart(dict(moves), height=170)
        misc_n = sum(len(t["misconceptions"]) for t in logs)
        check_n = sum(1 for t in logs if t["asked_check_question"])
        kpi_a, kpi_b = st.columns(2)
        kpi_a.metric("Hiểu lầm", misc_n)
        kpi_b.metric("Lượt kiểm tra", f"{check_n}/{len(logs)}")
    else:
        st.caption("Biểu đồ tiến trình sẽ xuất hiện sau khi bắt đầu học.")

with col_chat:
    st.markdown(
        '<div class="section-heading"><span>💬</span> Không gian học tập</div>',
        unsafe_allow_html=True,
    )
    topic_hint = st.text_input(
        "Ngữ cảnh bài học (tuỳ chọn)",
        value=st.session_state.get("topic_hint", ""),
        placeholder="Ví dụ: Context window · Binary Search · Problem Statement trang 3",
        help="Giúp tutor biết bạn đang học phần nào — câu hỏi kiểm tra sẽ sát hơn.",
        key="topic_hint",
    )
    # Khóa chiều cao khung chat; hội thoại dài sẽ cuộn bên trong thay vì
    # kéo dài toàn bộ trang và đẩy ô nhập xuống dưới.
    with st.container(height=520, border=True):
        if not st.session_state.messages:
            st.markdown(
                """
                <div class="empty-chat">
                  <div class="empty-icon">💡</div>
                  <div class="empty-title">Bạn muốn hiểu rõ điều gì hôm nay?</div>
                  <div class="empty-copy">
                    Hãy hỏi về một khái niệm, nhờ giải thích ví dụ,
                    hoặc thử diễn đạt điều bạn vừa học.
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        for msg in st.session_state.messages:
            # Streamlit chỉ nhận emoji chuẩn / path ảnh / "user"|"assistant"
            # Ký tự trang trí như "✦" sẽ bị hiểu nhầm thành path → crash.
            avatar = "🧑‍🎓" if msg["role"] == "student" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])
                if msg["role"] == "assistant" and msg.get("meta"):
                    m = msg["meta"]
                    follow_src = m.get("provider_followup", "template")
                    st.caption(
                        f"Hiểu bài {m['understanding_score']}%  ·  "
                        f"{m['teaching_strategy']}  ·  "
                        f"ước lượng:{m['provider_estimate']}  ·  "
                        f"câu hỏi:{follow_src}"
                    )

    prompt = st.chat_input("Nhập câu hỏi hoặc chia sẻ điều bạn vừa hiểu…")
    if prompt:
        st.session_state.messages.append({"role": "student", "content": prompt})
        history = [
            {"role": "student" if m["role"] == "student" else "tutor", "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]
        with st.spinner("Tutor đang phân tích cách học phù hợp với bạn…"):
            result = st.session_state.engine.run(
                prompt,
                history=history,
                topic_hint=topic_hint.strip(),
            )
        data = result.to_dict()
        st.session_state.turn_logs.append(data)
        st.session_state.messages.append(
            {"role": "assistant", "content": result.tutor_response, "meta": data}
        )
        st.rerun()

st.divider()
footer_left, footer_right = st.columns([3, 1])
with footer_left:
    with st.expander("VLearn Tutor có thể hỗ trợ gì?"):
        st.markdown(
            """
            - Ước lượng **mức độ hiểu** và gợi ý **bước học tiếp theo**.
            - Hỏi lại khi chưa đủ tín hiệu, không tự suy diễn hiểu lầm của bạn.
            - Đây là công cụ hỗ trợ học tập, **không phải điểm số chính thức**.
            """
        )
with footer_right:
    if st.button("↻  Bắt đầu lại", use_container_width=True):
        st.session_state.messages = []
        st.session_state.turn_logs = []
        st.rerun()

# ---------------------------------------------------------------------------
# Flow Lab — panel kiểm tra luồng (local data trước, API sau)
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    '<div class="section-heading"><span>🧪</span> Flow Lab · Kiểm tra luồng</div>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <div class="flow-banner">
      Thứ tự khi chạy 1 câu hỏi test:
      <b>1) Cache đĩa</b> → <b>2) Golden set</b> → <b>3) Gọi API Gemini</b> (chỉ khi miss).
      Dùng để kiểm tra pipeline trước demo / khi muốn tiết kiệm quota.
    </div>
    """,
    unsafe_allow_html=True,
)

if "flow_lab_result" not in st.session_state:
    st.session_state.flow_lab_result = None

lab_q_col, lab_opt_col = st.columns([2.2, 1], gap="large")
with lab_q_col:
    flow_question = st.text_area(
        "Câu hỏi test",
        height=100,
        placeholder=(
            "Dán câu hỏi học viên để xem hệ thống đọc dữ liệu nào…\n"
            "Ví dụ: \"Context\" là gì"
        ),
        key="flow_lab_question",
    )
    flow_topic = st.text_input(
        "Topic hint (tuỳ chọn)",
        placeholder="Context window / Stack vs Queue…",
        key="flow_lab_topic",
    )
with lab_opt_col:
    st.caption("Tuỳ chọn chạy")
    force_api = st.checkbox("Bỏ qua local · force gọi API", value=False)
    stats = cache_stats()
    st.metric("Cache entries", stats.get("total", 0))
    st.caption(
        f"api={stats.get('api', 0)} · golden={stats.get('golden_set', 0)}"
    )
    run_lab = st.button("▶ Chạy kiểm tra luồng", use_container_width=True, type="primary")
    clear_lab = st.button("Xoá kết quả panel", use_container_width=True)

if clear_lab:
    st.session_state.flow_lab_result = None
    st.rerun()

if run_lab:
    if not flow_question.strip():
        st.warning("Nhập câu hỏi test trước khi chạy.")
    else:
        with st.spinner("Đang lookup cache / golden-set / API…"):
            lab = run_flow_lab(
                flow_question.strip(),
                topic_hint=flow_topic.strip(),
                force_api=force_api,
            )
        st.session_state.flow_lab_result = lab.to_dict()
        st.rerun()

lab = st.session_state.flow_lab_result
if lab:
    source = lab["overall_source"]
    api_flag = "Có gọi API" if lab["api_called"] else "Không gọi API"
    matched = lab.get("matched_case_id") or "—"
    m1, m2, m3 = st.columns(3)
    m1.metric("Nguồn tổng", source)
    m2.metric("API", api_flag)
    m3.metric("Case khớp", matched)

    st.markdown("#### Trace từng bước")
    for step in lab["steps"]:
        src = step.get("source", "local")
        css = {
            "cache": "src-cache",
            "golden_set": "src-golden_set",
            "api": "src-api",
            "rule": "src-rule",
            "template": "src-template",
            "local": "src-local",
        }.get(src, "src-local")
        st.markdown(
            f"""
            <div class="flow-step">
              <div class="flow-step-title">
                <span>{escape(step.get("step", ""))}</span>
                <span class="src-pill {css}">{escape(src)}</span>
              </div>
              <div class="flow-step-detail">{escape(step.get("detail", ""))}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        data = step.get("data") or {}
        if data:
            with st.expander(f"Chi tiết · {step.get('step', '')}", expanded=False):
                st.json(data)

    result = lab.get("result") or {}
    if result:
        st.markdown("#### Output pipeline")
        c1, c2, c3 = st.columns(3)
        c1.metric("Understanding", f"{result.get('understanding_score', '—')}%")
        c2.metric("Strategy", result.get("teaching_strategy", "—"))
        c3.metric(
            "Providers",
            f"{result.get('provider_estimate')}/{result.get('provider_followup')}/{result.get('provider_response')}",
        )
        st.markdown("**Follow-up**")
        follows = result.get("follow_ups") or []
        st.info(follows[0] if follows else "—")
        st.markdown("**Tutor response**")
        st.write(result.get("tutor_response") or "—")
        with st.expander("JSON đầy đủ"):
            st.json(result)
else:
    st.caption(
        "Chưa có lần chạy Flow Lab. Thử dán một câu từ golden set "
        "(vd. `\"Context\" là gì`) để thấy HIT local, hoặc câu mới để gọi API."
    )