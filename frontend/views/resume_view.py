import streamlit as st
from frontend.components.api_client import api


def render_resume_view():
    st.markdown("### 📄 Resume Management & Semantic Extraction")
    st.markdown("Upload your resume to extract claimed skills and projects into your preparation profile.")
    st.markdown("<span class='credit-pill'>💡 Credit Control: AI is ONLY invoked when you explicitly click 'Analyze Resume'</span>", unsafe_allow_html=True)

    # 1. Upload Section
    uploaded_file = st.file_uploader("Upload Resume (PDF, DOCX, or TXT)", type=["pdf", "docx", "txt"])
    if uploaded_file:
        if st.button("Process & Store Resume", type="primary"):
            with st.spinner("Extracting text and computing resume hash..."):
                try:
                    bytes_data = uploaded_file.getvalue()
                    resume = api.upload_resume(bytes_data, uploaded_file.name)
                    st.success(f"Resume '{uploaded_file.name}' stored successfully (Version {resume.get('version')})!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Upload failed: {str(e)}")

    st.markdown("---")

    # 2. Latest Resume Display & Analysis Action
    try:
        latest_resume = api.get_latest_resume()
    except Exception:
        latest_resume = None

    if not latest_resume:
        st.info("No resume uploaded yet. Upload a resume above to begin.")
        return

    st.markdown(f"#### Active Resume: `{latest_resume.get('filename')}` (Version {latest_resume.get('version')})")
    
    col_act, col_info = st.columns([1, 2])
    with col_act:
        force = st.checkbox("Force re-analysis (bypass AI cache)", value=False)
        if st.button("🔍 Analyze Resume with AI", type="primary", use_container_width=True):
            with st.spinner("Analyzing resume semantics via Azure Foundry Agent..."):
                try:
                    res = api.analyze_resume(latest_resume["id"], force_refresh=force)
                    st.success("Resume analyzed successfully! Claimed skills and projects registered.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")

    with col_info:
        st.caption(f"SHA-256 Hash: `{latest_resume.get('file_hash')[:16]}...`")
        st.caption(f"Uploaded At: {latest_resume.get('uploaded_at')}")

    # 3. Parsed Data View
    parsed = latest_resume.get("parsed_data")
    if parsed:
        st.markdown("#### 📑 Extracted Resume Intelligence")
        
        # Summary & Projects
        st.markdown(f"**Executive Summary:** {parsed.get('summary', 'N/A')}")
        
        col_skills, col_projects = st.columns(2)
        with col_skills:
            st.markdown("##### 🛠️ Extracted Claimed Skills")
            for sk in parsed.get("skills", []):
                st.markdown(f"<span class='metric-badge badge-info'>{sk.get('name')} ({sk.get('claimed_level', 'Intermediate')})</span>", unsafe_allow_html=True)

        with col_projects:
            st.markdown("##### 🚀 Highlighted Projects")
            for p in parsed.get("projects", []):
                with st.expander(f"📌 {p.get('name')}", expanded=False):
                    st.write(p.get("description", ""))
                    st.caption(f"Tech: {', '.join(p.get('technologies', []))}")
                    for h in p.get("highlights", []):
                        st.markdown(f"- {h}")
    else:
        st.warning("This resume has not yet been analyzed. Click 'Analyze Resume with AI' to extract your skills.")
        with st.expander("View Raw Extracted Text"):
            st.text_area("Extracted Plain Text", value=latest_resume.get("raw_text", ""), height=200, disabled=True)
