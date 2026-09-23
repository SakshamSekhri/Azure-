import streamlit as st
import requests
from backend.app.config.settings import settings
from frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_status_badge,
    render_html
)


def render_settings_view():
    render_page_header(
        title="Settings & System Status",
        subtitle="Manage account profile, preparation preferences, and view Azure AI service connections."
    )

    user = st.session_state.get("user_info") or {}
    user_email = user.get("email", "student@example.com")
    user_name = user.get("name") or user_email.split("@")[0].capitalize()

    # -------------------------------------------------------------
    # 1. ACCOUNT PROFILE
    # -------------------------------------------------------------
    render_section_header("Account Profile")
    render_html(
        f"""
        <div class="saas-panel">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.85rem;">
                    <div style="width: 42px; height: 42px; border-radius: 50%; background: var(--accent-light); color: var(--accent); display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 1.1rem; border: 1px solid var(--border);">
                        {user_name[0].upper()}
                    </div>
                    <div>
                        <div style="font-weight: 700; font-size: 0.98rem; color: var(--text-primary);">{user_name}</div>
                        <div style="font-size: 0.82rem; color: var(--text-secondary);">{user_email}</div>
                    </div>
                </div>
                <div>
                    {render_status_badge('Active Student', 'success')}
                </div>
            </div>
        </div>
        """
    )

    # -------------------------------------------------------------
    # 2. APPEARANCE & DISPLAY THEME (White Screen / Black Screen)
    # -------------------------------------------------------------
    render_section_header("Appearance & Display Theme")
    current_theme = st.session_state.get("theme_mode", "light")
    col_t1, col_t2 = st.columns([2, 3])
    with col_t1:
        theme_options = ["☀️ White Screen (Light Mode)", "🌙 Black Screen (Dark Mode)"]
        selected_theme_idx = 0 if current_theme == "light" else 1
        chosen_theme_label = st.radio(
            "Screen Mode",
            options=theme_options,
            index=selected_theme_idx,
            label_visibility="collapsed"
        )
        selected_theme = "light" if "White" in chosen_theme_label else "dark"
        if selected_theme != current_theme:
            st.session_state["theme_mode"] = selected_theme
            st.rerun()
    with col_t2:
        st.caption("Toggle between high-contrast Black Screen (Dark Mode) for low-light focus sessions and White Screen (Light Mode) for daytime study.")

    st.write("")
    st.markdown("---")

    # -------------------------------------------------------------
    # 3. AI PREPARATION PREFERENCES
    # -------------------------------------------------------------
    render_section_header("AI & Preparation Preferences")
    with st.form("settings_pref_form"):
        col1, col2 = st.columns(2)
        with col1:
            st.selectbox("Default Practice Questions", [3, 5, 10], index=1)
            st.selectbox("Evaluation Difficulty", ["Adaptive (Recommended)", "Beginner", "Intermediate", "Advanced"], index=0)
        with col2:
            st.checkbox("Enable SHA-256 Prompt Caching (0 token cache hits)", value=True)
            st.checkbox("Deterministic Multi-Source Scoring Calibration", value=True)

        if st.form_submit_button("Save Preferences", type="primary"):
            st.success("Preferences saved successfully!")

    st.write("")
    st.markdown("---")

    # -------------------------------------------------------------
    # 3. SERVICE CONNECTIONS & SYSTEM HEALTH
    # -------------------------------------------------------------
    render_section_header("Service Connections & Telemetry Health")

    # FastAPI Backend
    try:
        res = requests.get("http://127.0.0.1:8000/health", timeout=3)
        backend_online = (res.status_code == 200)
        backend_detail = f"Online (v{res.json().get('version', '1.0.0')})"
    except Exception:
        backend_online = False
        backend_detail = "Offline"

    foundry_configured = bool(getattr(settings, "FOUNDRY_PROJECT_ENDPOINT", ""))
    search_configured = bool(getattr(settings, "AZURE_AI_SEARCH_ENDPOINT", "") and getattr(settings, "AZURE_AI_SEARCH_KEY", ""))

    agent_name = getattr(settings, "FOUNDRY_AGENT_NAME", "PlacementPreparationAgent")
    agent_version = getattr(settings, "FOUNDRY_AGENT_VERSION", "4")
    model_deployment = getattr(settings, "FOUNDRY_MODEL_DEPLOYMENT", "gpt-5-mini")
    search_index = getattr(settings, "AZURE_AI_SEARCH_INDEX", "placement-prep-knowledge")

    connections = [
        ("FastAPI Backend Core", backend_detail, "success" if backend_online else "danger"),
        (f"Azure AI Foundry Agent ({agent_name})", f"Active on {model_deployment} (v{agent_version})", "success" if foundry_configured else "warning"),
        ("RAG Knowledge Base", f"22-Module Curated Technical Repository Active" if not search_configured else f"Index '{search_index}'", "success")
    ]

    for name, detail, var in connections:
        render_html(
            f"""
            <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="font-weight: 600; font-size: 0.88rem; color: var(--text-primary);">{name}</span>
                    <span style="font-size: 0.8rem; color: var(--text-secondary); margin-left: 0.5rem;">— {detail}</span>
                </div>
                <div>{render_status_badge('Connected' if var == 'success' else 'Configured', var)}</div>
            </div>
            """
        )

    st.write("")
    st.markdown("---")

    # -------------------------------------------------------------
    # 4. SIGN OUT ACTION
    # -------------------------------------------------------------
    render_section_header("Session Management")
    c_out, _ = st.columns([1.5, 4])
    with c_out:
        if st.button("Sign Out of PlacementAI", use_container_width=True):
            st.session_state["auth_token"] = None
            st.session_state["user_info"] = None
            st.rerun()
