import streamlit as st
from frontend.components.api_client import api
from frontend.components.ui import render_html


def render_login_view():
    col_l, col_r = st.columns([6, 1.5])
    with col_r:
        is_dark = (st.session_state.get("theme_mode", "light") == "dark")
        toggle_label = "☀️ White Screen" if is_dark else "🌙 Black Screen"
        if st.button(toggle_label, key="login_theme_toggle", use_container_width=True):
            st.session_state["theme_mode"] = "light" if is_dark else "dark"
            st.rerun()

    render_html(
        """
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 2rem;">
            <div style="display: inline-flex; align-items: center; justify-content: center; width: 44px; height: 44px; background: #6366F1; color: white; border-radius: 10px; font-weight: 700; font-size: 20px; box-shadow: 0 4px 6px -1px rgba(99,102,241,0.25); margin-bottom: 0.75rem;">
                P
            </div>
            <h1 style="font-size: 1.85rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.025em; margin: 0 0 0.35rem 0;">
                PlacementAI
            </h1>
            <div style="font-size: 0.92rem; color: var(--text-secondary);">
                Modern AI-Powered Engineering Career & Placement Copilot
            </div>
        </div>
        """
    )

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        tab_login, tab_register, tab_demo = st.tabs(["Sign In", "Create Account", "⚡ Quick Demo"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="candidate@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In to PlacementAI", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        try:
                            api.login(email, password)
                            st.success("Authentication successful!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Authentication Error: {str(e)}")

        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input("Email Address", placeholder="candidate@example.com")
                reg_password = st.text_input("Password (min 6 characters)", type="password")
                reg_submitted = st.form_submit_button("Create Candidate Account", use_container_width=True, type="primary")

                if reg_submitted:
                    if not reg_email or len(reg_password) < 6:
                        st.error("Valid email and password (minimum 6 characters) required.")
                    else:
                        try:
                            api.register(reg_email, reg_password)
                            api.login(reg_email, reg_password)
                            st.success("Account created successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registration Error: {str(e)}")

        with tab_demo:
            render_html(
                """
                <div style="font-size: 0.84rem; color: var(--text-secondary); margin-bottom: 1rem; line-height: 1.45;">
                    Instant single-click demo access with pre-seeded engineering competencies, resume profile, and verified assessment history.
                </div>
                """
            )
            if st.button("Log In as Demo Candidate (student@example.com)", use_container_width=True, type="primary"):
                try:
                    api.login("student@example.com", "password123")
                    st.success("Logged in as Demo Student!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Demo Login Error: {str(e)}")

        render_html(
            """
            <div style="text-align: center; margin-top: 1.5rem; font-size: 0.76rem; color: var(--text-muted);">
                Protected by SHA-256 Credit Control & Azure AI Foundry
            </div>
            """
        )
