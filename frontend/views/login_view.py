import streamlit as st
from frontend.components.api_client import api


def render_login_view():
    st.markdown("<div style='text-align: center; margin-bottom: 2rem;'>", unsafe_allow_html=True)
    st.markdown("# 🚀 Placement Preparation Agent")
    st.markdown("##### Production-Ready AI-Powered Engineering Career Copilot")
    st.markdown("<span class='credit-pill'>🔒 Strict Credit Control & Deterministic Engine Active</span>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register, tab_demo = st.tabs(["🔑 Sign In", "📝 Create Account", "⚡ Quick Demo Access"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="student@example.com")
                password = st.text_input("Password", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Please provide both email and password.")
                    else:
                        try:
                            api.login(email, password)
                            st.success("Authentication successful! Redirecting to dashboard...")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Authentication Error: {str(e)}")

        with tab_register:
            with st.form("register_form"):
                reg_email = st.text_input("Email Address", placeholder="newstudent@university.edu")
                reg_password = st.text_input("Password (min 6 characters)", type="password")
                reg_submitted = st.form_submit_button("Create Account", use_container_width=True)

                if reg_submitted:
                    if not reg_email or len(reg_password) < 6:
                        st.error("Valid email and password (>= 6 chars) required.")
                    else:
                        try:
                            api.register(reg_email, reg_password)
                            api.login(reg_email, reg_password)
                            st.success("Account created and signed in! Welcome.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Registration Error: {str(e)}")

        with tab_demo:
            st.info("Instant access using pre-seeded test data and demo profile.")
            if st.button("Log In as Demo Student (student@example.com)", use_container_width=True, type="primary"):
                try:
                    api.login("student@example.com", "password123")
                    st.success("Logged in as Demo Student! Redirecting...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Demo Login Error: {str(e)}")
