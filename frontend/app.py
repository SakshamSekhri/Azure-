import streamlit as st
import sys
import os

# Append workspace root
sys.path.insert(0, os.path.abspath("."))

from frontend.components.styles import apply_custom_styles
from frontend.views.login_view import render_login_view
from frontend.views.dashboard_view import render_dashboard_view
from frontend.views.profile_view import render_profile_view
from frontend.views.resume_view import render_resume_view
from frontend.views.job_view import render_job_view
from frontend.views.skills_matrix_view import render_skills_matrix_view
from frontend.views.assessments_view import render_assessments_view
from frontend.views.learning_plan_view import render_learning_plan_view
from frontend.views.ai_usage_view import render_ai_usage_view
from frontend.views.settings_view import render_settings_view

# Page Config
st.set_page_config(
    page_title="Placement Preparation Agent",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply Modern Styling
apply_custom_styles()

# Authentication Guard
if "auth_token" not in st.session_state or not st.session_state["auth_token"]:
    render_login_view()
else:
    # Sidebar Navigation
    user = st.session_state.get("user_info") or {}
    user_email = user.get("email", "Student")

    st.sidebar.markdown(f"""
    <div style='padding: 0.5rem 0 1rem 0;'>
        <h3 style='margin: 0;'>🚀 Placement Prep</h3>
        <span style='font-size: 0.8rem; color: #64748b;'>{user_email}</span>
    </div>
    """, unsafe_allow_html=True)

    nav_selection = st.sidebar.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📄 Resume / CV Upload",
            "🎯 Target Job Description",
            "👤 Target Role & Profile",
            "📝 Personalized Assessment",
            "🧩 Skill Gaps & Readiness",
            "📅 Personalized Improvement Plan",
            "💳 AI Usage & Credit Audit",
            "⚙️ Settings"
        ]
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        st.session_state["auth_token"] = None
        st.session_state["user_info"] = None
        st.rerun()

    # Route Dispatch
    if nav_selection == "📊 Dashboard":
        render_dashboard_view()
    elif nav_selection == "📄 Resume / CV Upload":
        render_resume_view()
    elif nav_selection == "🎯 Target Job Description":
        render_job_view()
    elif nav_selection == "👤 Target Role & Profile":
        render_profile_view()
    elif nav_selection == "📝 Personalized Assessment":
        render_assessments_view()
    elif nav_selection == "🧩 Skill Gaps & Readiness":
        render_skills_matrix_view()
    elif nav_selection == "📅 Personalized Improvement Plan":
        render_learning_plan_view()
    elif nav_selection == "💳 AI Usage & Credit Audit":
        render_ai_usage_view()
    elif nav_selection == "⚙️ Settings":
        render_settings_view()
