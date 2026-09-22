import streamlit as st
import requests
from backend.app.config.settings import settings


def render_settings_view():
    st.markdown("### ⚙️ System Configuration & Azure Telemetry")
    st.markdown("Environment settings and service health.")

    st.markdown("##### 🔌 Backend API Connection")
    try:
        res = requests.get("http://127.0.0.1:8000/health", timeout=3)
        if res.status_code == 200:
            st.success(f"FastAPI Backend Connected: {res.json().get('service')} (v{res.json().get('version')})")
        else:
            st.warning(f"Backend returned status {res.status_code}")
    except Exception:
        st.error("Backend offline! Please run `uvicorn backend.app.main:app --reload`.")

    st.markdown("---")
    st.markdown("##### ☁️ Microsoft Foundry Agent Integration Status")
    foundry_configured = bool(settings.FOUNDRY_PROJECT_ENDPOINT)
    if foundry_configured:
        st.success(f"Microsoft Foundry Connected: Agent '{settings.FOUNDRY_AGENT_NAME}' (v{settings.FOUNDRY_AGENT_VERSION}) on gpt-5-mini")
    else:
        st.error("Microsoft Foundry endpoint not configured in `.env`. Question generation requires an active Microsoft Foundry agent.")

    st.markdown("##### 🔍 Azure AI Search Status")
    search_configured = bool(settings.AZURE_AI_SEARCH_ENDPOINT and settings.AZURE_AI_SEARCH_KEY)
    if search_configured:
        st.success(f"Azure AI Search Connected: Index '{settings.AZURE_AI_SEARCH_INDEX}'")
    else:
        st.info("Azure AI Search not configured in `.env`. Built-in curated educational knowledge base active.")

    st.markdown("---")
    st.markdown("##### 🚪 Session Management")
    if st.button("Sign Out of Account", type="primary"):
        st.session_state["auth_token"] = None
        st.session_state["user_info"] = None
        st.success("Signed out successfully.")
        st.rerun()
