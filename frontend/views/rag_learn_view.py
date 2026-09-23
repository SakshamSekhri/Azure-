import streamlit as st
from frontend.components.api_client import api
from frontend.components.ui import (
    render_page_header,
    render_status_badge,
    render_empty_state,
    render_html
)


def render_rag_learn_view():
    render_page_header(
        title="RAG Knowledge Assistant",
        subtitle="Conversational engineering copilot. Grounded in 22 curated guides and Azure AI Foundry."
    )

    # 3-Tier Status Overview Strip
    render_html(
        """
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.25rem;">
            <span class="status-badge badge-success">🟢 Tier 1: Verified Curated Docs</span>
            <span class="status-badge badge-info">💡 Tier 2: Core Engineering Synthesis</span>
            <span class="status-badge badge-neutral">🛡️ Tier 3: Technical Domain Guardrails</span>
        </div>
        """
    )

    # Initialize chat history in session state
    if "rag_chat_history" not in st.session_state:
        st.session_state["rag_chat_history"] = []

    # Check for incoming prefill query from other views
    prefill_q = st.session_state.pop("rag_prefill_query", None)
    prefill_t = st.session_state.pop("rag_prefill_topic", None)

    # Empty State & Suggested Prompts (if conversation is empty)
    if not st.session_state["rag_chat_history"] and not prefill_q:
        render_html(
            """
            <div style="text-align: center; padding: 2.5rem 1.5rem; background: var(--surface); border: 1px dashed var(--border); border-radius: 10px; margin-bottom: 1.5rem;">
                <div style="font-size: 1.8rem; margin-bottom: 0.4rem;">💬</div>
                <div style="font-size: 1.05rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.25rem;">Ask me anything about your placement preparation</div>
                <div style="font-size: 0.84rem; color: var(--text-secondary); max-width: 480px; margin: 0 auto 1.25rem auto;">
                    Inquire about system design trade-offs, algorithms, framework internals, or operating systems. Answers cite verified sources or synthesize core CS principles.
                </div>
            </div>
            """
        )

        render_html("<div style='font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.5rem;'>SUGGESTED TECHNICAL INQUIRIES</div>")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Explain B-Tree vs Hash index trade-offs", use_container_width=True):
                prefill_q = "Explain B-Tree vs Hash index trade-offs and composite leftmost prefix rules."
                prefill_t = "Databases"
            if st.button("🐍 How does the Python GIL affect concurrency?", use_container_width=True):
                prefill_q = "How does the Python Global Interpreter Lock (GIL) affect multithreading vs multiprocessing?"
                prefill_t = "Programming"
        with col2:
            if st.button("🐳 How do Linux namespaces work in Docker?", use_container_width=True):
                prefill_q = "How do Linux namespaces and cgroups isolate Docker containers?"
                prefill_t = "DevOps & Tools"
            if st.button("⚡ Kafka partitioning vs RabbitMQ queues", use_container_width=True):
                prefill_q = "What are the architectural differences between Apache Kafka and RabbitMQ?"
                prefill_t = "System Design"

    # Display Conversation History
    for msg in st.session_state["rag_chat_history"]:
        if msg["role"] == "user":
            render_html(f'<div class="chat-bubble-user">{msg["content"]}</div>')
        else:
            grounded = msg.get("grounded", False)
            citations = msg.get("citations", [])
            conf = msg.get("confidence", "Medium")
            answer_text = msg["content"]

            if str(conf).lower() == "none":
                tier_badge = render_status_badge("Tier 3: Domain Guardrail", "warning")
            elif grounded and citations:
                tier_badge = render_status_badge(f"Tier 1: Grounded Source ({conf})", "success")
            else:
                tier_badge = render_status_badge(f"Tier 2: Synthesized CS ({conf})", "info")

            citation_htmls = ""
            if citations:
                for c in citations:
                    citation_htmls += f"""
                    <div class="citation-box">
                        <strong style="color: var(--accent);">📌 {c.get('title', 'Curated Source')}</strong> 
                        <span style="color: var(--text-secondary); font-size: 0.78rem;">({c.get('source', '')})</span><br/>
                        <div style="font-style: italic; color: var(--text-secondary); margin-top: 0.2rem;">"{c.get('snippet', '')}"</div>
                    </div>
                    """

            render_html(
                f"""
                <div class="chat-bubble-ai">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-size: 0.76rem; font-weight: 700; color: var(--accent);">PLACEMENTAI ASSISTANT</span>
                        {tier_badge}
                    </div>
                    <div style="line-height: 1.55; color: var(--text-primary);">{answer_text}</div>
                    {f'<div style="margin-top: 0.75rem;"><span style="font-size: 0.76rem; font-weight: 600; color: var(--text-muted);">VERIFIED SOURCES:</span>{citation_htmls}</div>' if citations else ''}
                </div>
                """
            )

    # Handle incoming prefill query or user typed input
    user_query = st.chat_input("Ask anything about your placement preparation...")
    if prefill_q and not user_query:
        user_query = prefill_q

    if user_query:
        # Add user query to conversation history
        st.session_state["rag_chat_history"].append({"role": "user", "content": user_query})

        with st.spinner("Retrieving knowledge context and synthesizing engineering response..."):
            try:
                res = api.ask_rag_question(user_query, topic=prefill_t)
                st.session_state["rag_chat_history"].append({
                    "role": "assistant",
                    "content": res.get("answer", ""),
                    "grounded": res.get("grounded", False),
                    "citations": res.get("citations", []),
                    "confidence": res.get("confidence", "Medium")
                })
            except Exception as e:
                st.session_state["rag_chat_history"].append({
                    "role": "assistant",
                    "content": f"Query execution failed: {str(e)}",
                    "grounded": False,
                    "citations": [],
                    "confidence": "None"
                })

        st.rerun()

    # Clear Chat Action
    if st.session_state["rag_chat_history"]:
        st.write("")
        c_clear, _ = st.columns([1.5, 4])
        with c_clear:
            if st.button("Clear Conversation", use_container_width=True):
                st.session_state["rag_chat_history"] = []
                st.rerun()
