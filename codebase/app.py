"""Streamlit UI — Learning Engine Tutor (CP2/CP3)."""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learning_engine.llm_client import resolve_mode  # noqa: E402
from learning_engine.pipeline import LearningEngine  # noqa: E402

st.set_page_config(page_title="Learning Engine Tutor", page_icon="📚", layout="wide")

st.title("Learning Engine Tutor")
st.caption(
    "VLearn · Hướng A — từ Answer Engine sang Learning Engine: "
    "ước lượng hiểu bài → misconception → teaching move → follow-up."
)

mode = resolve_mode()
if mode == "mock":
    st.warning(
        "Đang chạy **mock** (chưa có GEMINI_API_KEY / OPENAI_API_KEY). "
        "Flow bấm được đủ cho CP2; để CP3 có LLM thật, thêm key vào `codebase/.env`."
    )
else:
    st.success(f"LLM provider: **{mode}** (Understanding Estimator gọi AI thật).")

if "engine" not in st.session_state:
    st.session_state.engine = LearningEngine()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "turn_logs" not in st.session_state:
    st.session_state.turn_logs = []

col_chat, col_side = st.columns([1.4, 1])

with col_side:
    st.subheader("Signals (turn mới nhất)")
    if st.session_state.turn_logs:
        last = st.session_state.turn_logs[-1]
        st.metric("Understanding", f"{last['understanding_score']}%")
        st.write(f"**Confidence:** {last['confidence']}")
        st.write(f"**Reason:** {last['understanding_reason']}")
        st.write(f"**Strategy:** `{last['teaching_strategy']}`")
        st.write(f"**asked_check_question:** {last['asked_check_question']}")
        st.write("**Misconceptions:**")
        st.write(last["misconceptions"] or "[]")
        st.write("**Follow-up:**")
        st.write(last["follow_ups"][0] if last["follow_ups"] else "—")
        if st.button("Bỏ qua follow-up / hỏi tự do (G8)"):
            st.info("Bạn có thể gõ câu hỏi tiếp ở khung chat — không bị chặn.")
    else:
        st.write("Chưa có turn nào.")

    st.divider()
    st.subheader("Dashboard KPI (session)")
    logs = st.session_state.turn_logs
    if logs:
        scores = [t["understanding_score"] for t in logs]
        st.line_chart({"understanding_score": scores})
        moves = Counter(t["teaching_strategy"] for t in logs)
        st.bar_chart(dict(moves))
        misc_n = sum(len(t["misconceptions"]) for t in logs)
        st.write(f"Tổng misconception phát hiện: **{misc_n}**")
        check_n = sum(1 for t in logs if t["asked_check_question"])
        st.write(f"Turns có check-question: **{check_n}/{len(logs)}**")
    else:
        st.caption("KPI hiện sau khi có hội thoại.")

with col_chat:
    st.subheader("Hội thoại")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and msg.get("meta"):
                m = msg["meta"]
                st.caption(
                    f"score={m['understanding_score']}% · {m['teaching_strategy']} · "
                    f"provider={m['provider_estimate']}"
                )

    prompt = st.chat_input("Hỏi tutor về khái niệm đang học…")
    if prompt:
        st.session_state.messages.append({"role": "student", "content": prompt})
        history = [
            {"role": "student" if m["role"] == "student" else "tutor", "content": m["content"]}
            for m in st.session_state.messages[:-1]
        ]
        result = st.session_state.engine.run(prompt, history=history)
        data = result.to_dict()
        st.session_state.turn_logs.append(data)
        st.session_state.messages.append(
            {"role": "assistant", "content": result.tutor_response, "meta": data}
        )
        st.rerun()

with st.expander("Phạm vi hệ thống (G1)"):
    st.markdown(
        """
- Ước lượng **mức hiểu** + gợi ý **bước học tiếp** — **không** chấm điểm chính thức.
- Khi tín hiệu mỏng (`confidence=low`) sẽ hỏi làm rõ, không bịa misconception (G10).
- Bạn luôn bỏ qua follow-up và hỏi tiếp tự do được (G8).
        """
    )

if st.button("Reset hội thoại"):
    st.session_state.messages = []
    st.session_state.turn_logs = []
    st.rerun()
