import streamlit as st
from frontend.components.api_client import api


def render_rag_learn_view():
    st.markdown("### 📚 Grounded RAG Educational Assistant")
    st.markdown("Ask technical and architectural questions. Answers are strictly grounded in retrieved educational sources with full citations.")
    st.markdown("<span class='credit-pill'>🔒 Grounded RAG: Zero Hallucination — Explicit Source Citations</span>", unsafe_allow_html=True)

    with st.form("rag_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            question = st.text_input(
                "Your Technical Question",
                placeholder="e.g. How does FastAPI dependency injection manage database connection lifecycles?"
            )
        with col2:
            topic = st.selectbox("Topic Focus (Optional)", ["All", "Databases", "Backend Frameworks", "System Design", "Programming", "DevOps & Tools"])

        submitted = st.form_submit_button("Ask Grounded Assistant", type="primary", use_container_width=True)

    if submitted:
        if not question or len(question.strip()) < 3:
            st.error("Please enter a valid technical question.")
        else:
            with st.spinner("Searching Azure AI Search knowledge base and synthesizing grounded answer..."):
                try:
                    topic_arg = None if topic == "All" else topic
                    result = api.ask_rag_question(question, topic=topic_arg)
                    st.session_state["last_rag_result"] = result
                except Exception as e:
                    st.error(f"Query failed: {str(e)}")

    # Display Answer & Citations
    res = st.session_state.get("last_rag_result")
    if res:
        st.markdown("---")
        st.markdown(f"#### 💡 Grounded Answer")
        st.write(res.get("answer", ""))

        citations = res.get("citations", [])
        if citations:
            st.markdown("##### 📖 Educational Citations & Source Grounds:")
            for c in citations:
                st.markdown(f"""
                <div class="citation-box">
                    <strong>📌 {c.get('title')}</strong> ({c.get('source')})<br/>
                    <em>"{c.get('snippet')}"</em>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("No specific source document matched this inquiry directly.")
