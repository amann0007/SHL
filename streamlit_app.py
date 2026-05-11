import streamlit as st

from main import Message, call_agent


st.set_page_config(
        page_title="SHL Advisor",
        page_icon="🧾",
        layout="wide",
        initial_sidebar_state="expanded",
)

st.markdown(
        """
        <style>
            :root { color-scheme: light; }
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(200, 16, 46, 0.08), transparent 28%),
                    linear-gradient(180deg, #fbfbfd 0%, #f4f5f9 100%);
            }
            .block-container {
                padding-top: 1rem;
                padding-bottom: 0.75rem;
                max-width: 1200px;
            }
            [data-testid="stSidebar"] {
                background: linear-gradient(180deg, #ffffff 0%, #fafbff 100%);
                border-right: 1px solid #ececf1;
            }
            [data-testid="stHeader"] { background: transparent; }
            footer, #MainMenu { visibility: hidden; }
            .hero {
                background: rgba(255, 255, 255, 0.75);
                border: 1px solid rgba(255,255,255,0.9);
                backdrop-filter: blur(14px);
                border-radius: 24px;
                padding: 1.15rem 1.25rem;
                box-shadow: 0 18px 42px rgba(17, 17, 34, 0.08);
                margin-bottom: 1rem;
            }
            .title {
                font-size: 2.35rem;
                line-height: 1.05;
                font-weight: 800;
                letter-spacing: -0.04em;
                margin-bottom: 0.35rem;
            }
            .subtitle {
                color: #5b5b6a;
                margin-bottom: 0.9rem;
                max-width: 64ch;
            }
            .hero-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.75rem;
            }
            .mini-card,
            .card {
                background: #ffffff;
                border: 1px solid #ececf1;
                border-radius: 18px;
                box-shadow: 0 10px 24px rgba(0,0,0,0.05);
            }
            .mini-card {
                padding: 0.85rem 0.95rem;
            }
            .mini-card strong {
                display: block;
                margin-bottom: 0.25rem;
            }
            .mini-card span,
            .muted {
                color: #63637a;
                font-size: 0.95rem;
            }
            .card {
                padding: 1rem 1.05rem;
                margin-bottom: 0.75rem;
            }
            .card h4 {
                margin: 0 0 0.35rem 0;
            }
            .card p {
                margin: 0.2rem 0;
                color: #444;
            }
            .message-wrap {
                margin-top: 0.9rem;
            }
            .msg-row {
                display: flex;
                gap: 0.75rem;
                margin-bottom: 0.85rem;
                align-items: flex-start;
            }
            .msg-row.user {
                flex-direction: row-reverse;
            }
            .bubble {
                max-width: min(820px, 100%);
                padding: 0.95rem 1rem;
                border-radius: 18px;
                box-shadow: 0 10px 26px rgba(0,0,0,0.06);
            }
            .bubble.user {
                background: #1f2030;
                color: #fff;
                border-top-right-radius: 8px;
            }
            .bubble.assistant {
                background: #fff;
                color: #1f2230;
                border: 1px solid #ececf1;
                border-top-left-radius: 8px;
            }
            .avatar-dot {
                width: 2.1rem;
                height: 2.1rem;
                border-radius: 999px;
                display: grid;
                place-items: center;
                flex: 0 0 auto;
                font-size: 1rem;
                font-weight: 700;
            }
            .avatar-dot.user {
                background: #1f2030;
                color: #fff;
            }
            .avatar-dot.assistant {
                background: #c8102e;
                color: #fff;
            }
            .quick-actions {
                display: flex;
                flex-wrap: wrap;
                gap: 0.6rem;
                margin: 0.75rem 0 0.25rem;
            }
            .quick-actions button {
                background: #fff;
                border: 1px solid #d9dbe7;
                color: #1f2230;
                padding: 0.6rem 0.9rem;
                border-radius: 999px;
                cursor: pointer;
                font-weight: 600;
            }
            .quick-actions button:hover {
                border-color: #c8102e;
                color: #c8102e;
            }
        </style>
        """,
        unsafe_allow_html=True,
)

st.markdown(
        """
        <div class="hero">
            <div class="title">SHL Advisor</div>
            <div class="subtitle">A local SHL assessment recommender that runs in your browser and returns real catalog matches.</div>
            <div class="hero-grid">
                <div class="mini-card"><strong>Fast setup</strong><span>Open the local URL and start chatting immediately.</span></div>
                <div class="mini-card"><strong>Real catalog</strong><span>Recommendations are pulled from the SHL catalog only.</span></div>
                <div class="mini-card"><strong>Browser-ready</strong><span>No separate API UI is needed for day-to-day use.</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
)

with st.sidebar:
        st.subheader("Assessment Selector")
        st.write("Try requests like:")
        st.caption("Data scientist hiring — mid-level")
        st.caption("I need assessments for a software engineer role")
        st.caption("Leadership assessments for managers")
        if st.button("Reset chat", use_container_width=True):
                st.session_state.messages = []
                st.rerun()


if "messages" not in st.session_state:
        st.session_state.messages = []


def render_recommendations(recommendations):
    if recommendations:
        st.markdown("#### Recommended assessments")
        for rec in recommendations:
            if hasattr(rec, "model_dump"):
                rec = rec.model_dump()
            st.markdown(
                f"""
                <div class="card">
                    <h4><a href="{rec['url']}" target="_blank">{rec['name']}</a></h4>
                    <p class="muted">Type: {rec['test_type']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def submit_prompt(prompt: str):
        st.session_state.messages.append({"role": "user", "content": prompt})
        result = call_agent([Message(**message) for message in st.session_state.messages])
        st.session_state.messages.append(
                {
                        "role": "assistant",
                        "content": result.reply,
                        "recommendations": [rec.model_dump() for rec in result.recommendations],
                }
        )
        st.rerun()


if not st.session_state.messages:
        st.markdown(
                """
                <div class="card">
                    <h4>Start with a role</h4>
                    <p class="muted">Try something like “Data scientist hiring — mid-level” or “I need assessments for a software engineer role”.</p>
                </div>
                """,
                unsafe_allow_html=True,
        )
        st.markdown('<div class="quick-actions">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
                if st.button("Data scientist — mid-level", use_container_width=True):
                        submit_prompt("Data scientist hiring — mid-level")
        with col2:
                if st.button("Software engineer role", use_container_width=True):
                        submit_prompt("I need assessments for a software engineer role")
        with col3:
                if st.button("Leadership assessments", use_container_width=True):
                        submit_prompt("Leadership assessments for managers")
        st.markdown("</div>", unsafe_allow_html=True)


st.markdown('<div class="message-wrap">', unsafe_allow_html=True)
for item in st.session_state.messages:
        role = item["role"]
        bubble_text = item["content"]
        recommendations = item.get("recommendations", [])
        st.markdown(
                f'<div class="msg-row {role}"><div class="avatar-dot {role}">{"Y" if role == "user" else "S"}</div><div class="bubble {role}">{bubble_text}</div></div>',
                unsafe_allow_html=True,
        )
        if role == "assistant" and recommendations:
            render_recommendations(recommendations)

if prompt := st.chat_input("Describe the role or what you're looking for..."):
        submit_prompt(prompt)

st.markdown("</div>", unsafe_allow_html=True)
