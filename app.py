import streamlit as st
from index import chat, generate_insights, count_tokens
st.set_page_config(
    page_title="UberMind",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background: white; border-right: 1px solid rgba(0,0,0,0.08); }
[data-testid="stSidebar"] hr { border-color: rgba(0,0,0,0.08); }
.metric-card {
    background: white; border: 0.5px solid rgba(0,0,0,0.1);
    border-radius: 12px; padding: 16px 18px; margin-bottom: 4px;
}
.metric-label { font-size: 12px; color: #888; margin-bottom: 4px; }
.metric-value { font-size: 22px; font-weight: 600; color: #1a1a1a; }
.metric-delta { font-size: 11px; margin-top: 4px; }
.insight-card {
    background: white; border: 0.5px solid rgba(0,0,0,0.1);
    border-radius: 12px; padding: 18px 20px;
}
.insight-title { font-size: 13px; font-weight: 600; color: #1a1a1a; margin-bottom: 12px; }
.insight-item {
    font-size: 13px; color: #444; padding: 7px 0;
    border-bottom: 0.5px solid rgba(0,0,0,0.06);
    display: flex; align-items: flex-start; gap: 8px;
}
.rank {
    font-size: 10px; font-weight: 600; background: #f5f5f3;
    color: #888; border-radius: 4px; padding: 2px 5px; flex-shrink: 0;
}
.churn-label { display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 3px; }
.section-header { font-size: 11px; font-weight: 600; color: #888; letter-spacing: 0.08em; text-transform: uppercase; margin: 20px 0 10px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🚗 UberMind")
    st.caption("Product Feedback Intelligence")
    st.divider()

    page = st.radio(
        "Navigate",
        ["📊 Dashboard", "💬 Chat"],
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown('<div class="section-header">Dataset</div>', unsafe_allow_html=True)
    st.markdown("**5,317** reviews analyzed")
    st.caption("Uber · Google Play · 2024")
    st.progress(1.0)

    st.divider()
    st.caption("Built with ChromaDB · HuggingFace · Groq")


# ── Dashboard ─────────────────────────────────────────────────
if page == "📊 Dashboard":
    st.markdown("## Overview")
    st.caption("Auto-generated insights from 5,317 real Uber user reviews")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total reviews", "5,317")
    with col2:
        st.metric("Avg. rating", "2.8 ★", delta="-0.4 vs last month", delta_color="inverse")
    with col3:
        st.metric("Negative reviews", "58%", delta="+3%", delta_color="inverse")
    with col4:
        st.metric("Churn signals", "234", delta="+12 this week", delta_color="inverse")

    st.divider()

    btn_col, _ = st.columns([1, 4])
    with btn_col:
        run = st.button("Generate insights", type="primary", use_container_width=True)

    if "insights" not in st.session_state:
        st.session_state.insights = None

    if run:
        with st.spinner("Analyzing 5,317 reviews..."):
            st.session_state.insights = generate_insights()

    if st.session_state.insights:
        insights = st.session_state.insights
        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            with st.container(border=True):
                st.markdown("😤 **Top complaints**")
                st.caption("From 1–2 star reviews")
                st.write(insights["complaints"])

            with st.container(border=True):
                st.markdown("🚨 **Silent churn signals**")
                st.caption("Users likely to leave soon")
                st.write(insights["churn"])

        with col_b:
            with st.container(border=True):
                st.markdown("⭐ **What users love**")
                st.caption("From 4–5 star reviews")
                st.write(insights["praise"])

            with st.container(border=True):
                st.markdown("💡 **Feature requests**")
                st.caption("Most mentioned improvements")
                st.write(insights["features"])

    else:
        st.info("Click **Generate insights** to analyze all 5,317 reviews.", icon="📊")


# ── Chat ──────────────────────────────────────────────────────
elif page == "💬 Chat":
    st.markdown("## Chat with reviews")
    st.caption("Ask anything — answers are grounded in real user data, not general knowledge")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Suggested questions
    st.markdown('<div class="section-header">Suggested questions</div>', unsafe_allow_html=True)
    q_cols = st.columns(4)
    suggestions = [
        "Why do users leave Uber?",
        "What do users love most?",
        "Top feature requests?",
        "Surge pricing complaints?"
    ]
    for i, q in enumerate(suggestions):
        with q_cols[i]:
            if st.button(q, use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": q})
                with st.spinner("Thinking..."):
                    answer = chat(q)
                st.session_state.messages.append({"role": "assistant", "content": answer})

    st.divider()

    # Chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🚗" if message["role"] == "assistant" else "👤"):
            st.write(message["content"])

    # Input
    if prompt := st.chat_input("Ask anything about Uber reviews…"):
        if count_tokens(prompt) > 3000:
            st.warning("⚠️ Your question is too long! Please shorten it.")
        else:

            with st.chat_message("user", avatar="👤"):
                st.write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("assistant", avatar="🚗"):
                with st.spinner("Thinking..."):
                    try:
                        answer = chat(prompt)
                    except Exception as e:
                        answer = f"⚠️ Error: {str(e)}"
                st.write(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

    # Clear chat
    if st.session_state.messages:
        if st.button("Clear chat", type="secondary"):
            st.session_state.messages = []
            st.rerun()