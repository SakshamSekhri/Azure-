import streamlit as st
import sys
import os

# Append workspace root
sys.path.insert(0, os.path.abspath("."))

from frontend.components.styles import apply_custom_styles
from frontend.components.ui import render_html
from frontend.views.login_view import render_login_view
from frontend.views.dashboard_view import render_dashboard_view
from frontend.views.resume_view import render_resume_view
from frontend.views.job_view import render_job_view
from frontend.views.skills_matrix_view import render_skills_matrix_view
from frontend.views.assessments_view import render_assessments_view
from frontend.views.learning_plan_view import render_learning_plan_view
from frontend.views.skill_topic_view import render_skill_topic_view
from frontend.views.rag_learn_view import render_rag_learn_view
from frontend.views.ai_usage_view import render_ai_usage_view
from frontend.views.settings_view import render_settings_view

# Page Config
st.set_page_config(
    page_title="PlacementAI — Engineering Career Copilot",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme State (Light / Dark)
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "light"

# Apply Centralized SaaS Styling
apply_custom_styles(theme=st.session_state["theme_mode"])

# Authentication Guard
if "auth_token" not in st.session_state or not st.session_state["auth_token"]:
    render_login_view()
else:
    user = st.session_state.get("user_info") or {}
    user_email = user.get("email", "student@example.com")
    user_name = user.get("name") or user_email.split("@")[0].capitalize()
    user_initial = user_name[0].upper() if user_name else "S"

    # 1. Sidebar Brand Header
    render_html(
        """
        <div style="padding: 0.2rem 0.2rem 1rem 0.2rem; display: flex; align-items: center; gap: 0.55rem;">
            <div style="background: #6366F1; color: white; width: 28px; height: 28px; border-radius: 7px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; box-shadow: 0 1px 2px rgba(99,102,241,0.3);">P</div>
            <div>
                <span style="font-size: 1.02rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em;">PlacementAI</span>
                <span style="font-size: 0.68rem; font-weight: 600; color: var(--accent); background: var(--accent-light); padding: 0.1rem 0.4rem; border-radius: 4px; margin-left: 0.3rem;">PRO</span>
            </div>
        </div>
        """,
        sidebar=True
    )

    # 2. Grouped SaaS Navigation Structure
    NAV_GROUPS = [
        {
            "group": "OVERVIEW",
            "items": [
                ("Dashboard", "📊 Dashboard")
            ]
        },
        {
            "group": "PROFILE",
            "items": [
                ("Resume / CV", "📄 Resume / CV"),
                ("Target Job", "💼 Target Job"),
                ("Skills Gaps & Readiness", "🧩 Skills & Readiness")
            ]
        },
        {
            "group": "PREPARATION",
            "items": [
                ("Skills & Topic Practice", "🎯 Skills & Topics"),
                ("Personalized Assessment", "📝 Assessments"),
                ("Personalized Improvement Plan", "📅 Improvement Plan")
            ]
        },
        {
            "group": "AI TOOLS",
            "items": [
                ("RAG Assistant", "📚 RAG Assistant")
            ]
        },
        {
            "group": "ACCOUNT",
            "items": [
                ("Usage & Credit Audit", "💳 Usage & Credits"),
                ("Settings", "⚙️ Settings")
            ]
        }
    ]

    ALL_PAGES = [
        "Dashboard",
        "Resume / CV",
        "Target Job",
        "Skills Gaps & Readiness",
        "Skills & Topic Practice",
        "Personalized Assessment",
        "Personalized Improvement Plan",
        "RAG Assistant",
        "Usage & Credit Audit",
        "Settings"
    ]

    def _resolve_nav_target(target: str) -> str:
        if not target:
            return "Dashboard"
        cleaned = target.lower().strip()
        # Direct clean match against canonical names
        for p in ALL_PAGES:
            if p.lower() == cleaned:
                return p
        # Match without emoji or partial match
        for p in ALL_PAGES:
            p_clean = p.lower()
            if p_clean in cleaned or cleaned in p_clean:
                return p
            # Match keywords
            if "practice" in cleaned and "practice" in p_clean:
                return "Skills & Topic Practice"
            if "assess" in cleaned and "assessment" in p_clean:
                return "Personalized Assessment"
            if "plan" in cleaned and "plan" in p_clean:
                return "Personalized Improvement Plan"
            if "resume" in cleaned and "resume" in p_clean:
                return "Resume / CV"
            if "job" in cleaned and "job" in p_clean:
                return "Target Job"
            if ("gap" in cleaned or "readiness" in cleaned) and "readiness" in p_clean:
                return "Skills Gaps & Readiness"
            if "rag" in cleaned or "learn" in cleaned:
                return "RAG Assistant"
            if "usage" in cleaned or "credit" in cleaned:
                return "Usage & Credit Audit"
            if "setting" in cleaned:
                return "Settings"
        return "Dashboard"

    # Handle pending programmatic navigation redirect
    if "pending_nav" in st.session_state:
        resolved = _resolve_nav_target(st.session_state.pop("pending_nav"))
        st.session_state["current_nav"] = resolved
    elif "current_nav" not in st.session_state or st.session_state["current_nav"] not in ALL_PAGES:
        # Fallback to legacy nav_choice if set
        legacy = st.session_state.get("nav_choice")
        st.session_state["current_nav"] = _resolve_nav_target(legacy) if legacy else "Dashboard"

    current_page = st.session_state["current_nav"]

    # Render Grouped Navigation in Sidebar
    for group_def in NAV_GROUPS:
        render_html(f'<div class="sidebar-section-label">{group_def["group"]}</div>', sidebar=True)
        for page_key, display_label in group_def["items"]:
            is_active = (current_page == page_key)
            btn_type = "primary" if is_active else "secondary"
            if st.sidebar.button(
                display_label,
                key=f"nav_btn_{page_key}",
                type=btn_type,
                use_container_width=True
            ):
                st.session_state["current_nav"] = page_key
                st.session_state["nav_choice"] = page_key
                st.rerun()

    # 3. Theme Mode (Black Screen / White Screen) Toggle
    is_dark = (st.session_state.get("theme_mode", "light") == "dark")
    toggle_label = "☀️ White Screen (Light Mode)" if is_dark else "🌙 Black Screen (Dark Mode)"
    if st.sidebar.button(toggle_label, key="sidebar_theme_toggle", use_container_width=True):
        st.session_state["theme_mode"] = "light" if is_dark else "dark"
        st.rerun()

    # 4. User Profile & Sign Out Footer
    render_html(
        f"""
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border);">
            <div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.75rem;">
                <div style="width: 32px; height: 32px; border-radius: 50%; background: var(--accent-light); color: var(--accent); display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: 0.85rem; border: 1px solid var(--border);">
                    {user_initial}
                </div>
                <div style="overflow: hidden; line-height: 1.2;">
                    <div style="font-size: 0.84rem; font-weight: 600; color: var(--text-primary); text-overflow: ellipsis; white-space: nowrap;">{user_name}</div>
                    <div style="font-size: 0.74rem; color: var(--text-secondary); text-overflow: ellipsis; white-space: nowrap;">{user_email}</div>
                </div>
            </div>
        </div>
        """,
        sidebar=True
    )

    if st.sidebar.button("Sign Out", key="sidebar_sign_out_btn", use_container_width=True):
        st.session_state["auth_token"] = None
        st.session_state["user_info"] = None
        st.rerun()

    # Route Dispatch for exact 10 Navigation Items
    if current_page == "Dashboard":
        render_dashboard_view()
    elif current_page == "Skills Gaps & Readiness":
        render_skills_matrix_view()
    elif current_page == "Personalized Improvement Plan":
        render_learning_plan_view()
    elif current_page == "Skills & Topic Practice":
        render_skill_topic_view()
    elif current_page == "Resume / CV":
        render_resume_view()
    elif current_page == "Target Job":
        render_job_view()
    elif current_page == "Personalized Assessment":
        render_assessments_view()
    elif current_page == "RAG Assistant":
        render_rag_learn_view()
    elif current_page == "Usage & Credit Audit":
        render_ai_usage_view()
    elif current_page == "Settings":
        render_settings_view()
    else:
        render_dashboard_view()
