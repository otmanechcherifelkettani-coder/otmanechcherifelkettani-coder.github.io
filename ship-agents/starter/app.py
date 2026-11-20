"""A shippable UI in ~40 lines: chat + a one-tap flag button that feeds your error analysis.

    streamlit run app.py

Deploy free: push this folder to GitHub, then Streamlit Community Cloud or a Hugging Face Space (Streamlit SDK).
Put ANTHROPIC_API_KEY in the platform's secrets, never in the repo.
"""
import json
import pathlib
import time

import streamlit as st

import agent

FLAGS = pathlib.Path(__file__).parent / "traces" / "flags.jsonl"

st.set_page_config(page_title="Atlas Telecom support", page_icon="📶")
st.title("Atlas Telecom — support")
st.caption("Demo agent on synthetic data. Try: “Coupure fibre à Maarif, Salma 0661234567”.")

if "history" not in st.session_state:
    st.session_state.history, st.session_state.chat = [], []

for i, (role, text, run_id) in enumerate(st.session_state.chat):
    with st.chat_message(role):
        st.write(text)
        if role == "assistant" and st.button("Flag this answer", key=f"flag-{i}"):
            FLAGS.parent.mkdir(exist_ok=True)
            with FLAGS.open("a", encoding="utf-8") as f:
                f.write(json.dumps({"ts": time.time(), "run_id": run_id, "reply": text}, ensure_ascii=False) + "\n")
            st.toast("Flagged. It will show up in error analysis.")

if prompt := st.chat_input("Écrivez votre message…"):
    st.session_state.chat.append(("user", prompt, None))
    with st.spinner("…"):
        out = agent.run(prompt, history=st.session_state.history)
    st.session_state.history = out["messages"]
    st.session_state.chat.append(("assistant", out["reply"], out["run_id"]))
    st.rerun()
