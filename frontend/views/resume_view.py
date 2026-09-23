import streamlit as st
from frontend.components.api_client import api
from frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_progress_bar,
    render_status_badge,
    render_empty_state,
    render_html
)


def render_resume_view():
    render_page_header(
        title="Resume Analysis",
        subtitle="Semantic skill extraction, background profiling, and job alignment analysis."
    )

    try:
        latest_resume = api.get_latest_resume()
    except Exception:
        latest_resume = None

    try:
        dash_data = api.get_dashboard_summary()
    except Exception:
        dash_data = {}

    target_role = dash_data.get("target_role", "Engineering Candidate")
    resume_match = round(dash_data.get("resume_match_percentage", 0.0), 1)

    # 1. Top Summary Panel (Linear / Vercel style)
    c_summary, c_upload = st.columns([2.5, 1.5])
    with c_summary:
        if latest_resume:
            render_html(
                f"""
                <div class="saas-panel">
                    <div style="font-size: 0.72rem; font-weight: 700; color: #6366F1; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.2rem;">
                        ACTIVE CANDIDATE PROFILE
                    </div>
                    <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">
                        <h2 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: var(--text-primary);">{latest_resume.get('filename')}</h2>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">Version {latest_resume.get('version', 1)} • {latest_resume.get('uploaded_at', '')[:10]}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 1rem; margin-top: 0.6rem;">
                        <span style="font-size: 0.84rem; color: var(--text-secondary);">Target Role: <strong>{target_role}</strong></span>
                        <span style="font-size: 0.84rem; color: var(--text-secondary);">Resume Match: <strong style="color: {'#10B981' if resume_match >= 75 else '#F59E0B'};">{resume_match}%</strong></span>
                    </div>
                    <div class="saas-bar-track" style="height: 6px; max-width: 320px; margin-top: 0.5rem;">
                        <div class="saas-bar-fill" style="width: {min(100.0, resume_match)}%; background-color: {'#10B981' if resume_match >= 75 else '#6366F1'};"></div>
                    </div>
                </div>
                """
            )
        else:
            render_empty_state("No Active Resume", "Upload a PDF or DOCX resume to extract your baseline profile.", icon="📄")

    with c_upload:
        with st.popover("📤 Upload / Replace Resume", use_container_width=True):
            uploaded_file = st.file_uploader("Choose Resume File", type=["pdf", "docx", "txt"])
            if uploaded_file and st.button("Save & Upload", type="primary", use_container_width=True):
                with st.spinner("Uploading and hashing resume..."):
                    try:
                        bytes_data = uploaded_file.getvalue()
                        res = api.upload_resume(bytes_data, uploaded_file.name)
                        st.success(f"Uploaded {uploaded_file.name} successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Upload failed: {str(e)}")

        if latest_resume:
            force_refresh = st.checkbox("Force fresh re-analysis", value=False)
            if st.button("🔍 Analyze Resume with AI", type="primary", use_container_width=True):
                with st.spinner("Analyzing resume semantics via Azure AI Foundry..."):
                    try:
                        api.analyze_resume(latest_resume["id"], force_refresh=force_refresh)
                        st.success("Resume analyzed successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Analysis error: {str(e)}")

    if not latest_resume or not latest_resume.get("parsed_data"):
        if latest_resume:
            st.info("Resume file is uploaded. Click **'Analyze Resume with AI'** above to extract skills and project intelligence.")
        return

    parsed = latest_resume["parsed_data"]
    st.markdown("---")

    # -------------------------------------------------------------
    # 2. DETECTED SKILLS & RECOMMENDED SKILLS
    # -------------------------------------------------------------
    col_det, col_rec = st.columns(2)

    with col_det:
        render_section_header("Detected Claimed Skills")
        skills_list = parsed.get("skills", [])
        if skills_list:
            pill_htmls = []
            for sk in skills_list:
                level_str = sk.get("claimed_level", "Intermediate")
                pill_htmls.append(
                    f"<span class='status-badge badge-info' style='margin-right: 0.35rem; margin-bottom: 0.35rem;'>"
                    f"<strong>{sk.get('name')}</strong> • {level_str}</span>"
                )
            render_html(f"<div style='display: flex; flex-wrap: wrap;'>{''.join(pill_htmls)}</div>")
        else:
            st.caption("No specific skills identified.")

    with col_rec:
        render_section_header("Missing / Recommended Skills", "Identified from your target job description")
        try:
            cand_jd = api.get_candidate_vs_jd()
            missing_skills = cand_jd.get("skill_gaps", []) if cand_jd else []
        except Exception:
            missing_skills = []

        if missing_skills:
            rec_pills = []
            for m_skill in missing_skills:
                rec_pills.append(
                    f"<span class='status-badge badge-warning' style='margin-right: 0.35rem; margin-bottom: 0.35rem;'>"
                    f"⚠️ {m_skill}</span>"
                )
            render_html(f"<div style='display: flex; flex-wrap: wrap;'>{''.join(rec_pills)}</div>")
        else:
            st.caption("No critical missing skills detected against your target job.")

    st.write("")
    st.markdown("---")

    # -------------------------------------------------------------
    # 3. EXECUTIVE SUMMARY & PROFILE HIGHLIGHTS
    # -------------------------------------------------------------
    c_name = parsed.get("candidate_name")
    c_email = parsed.get("email")
    c_summary = parsed.get("summary")

    if c_name or c_email or c_summary:
        render_section_header("Candidate Profile & Summary")
        if c_name or c_email:
            render_html(f"<div style='font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.35rem;'><strong>Candidate:</strong> {c_name or 'N/A'} &nbsp;|&nbsp; <strong>Email:</strong> {c_email or 'N/A'}</div>")
        if c_summary:
            render_html(
                f"""
                <div style="background: var(--surface); border-left: 3px solid var(--accent); padding: 0.75rem 1rem; border-radius: 0 6px 6px 0; font-size: 0.86rem; color: var(--text-primary); line-height: 1.5;">
                    {c_summary}
                </div>
                """
            )

    st.write("")

    # -------------------------------------------------------------
    # 4. PROJECTS & WORK EXPERIENCE
    # -------------------------------------------------------------
    col_proj, col_exp = st.columns(2)

    with col_proj:
        render_section_header("Extracted Projects")
        projects = parsed.get("projects", [])
        if projects:
            for p in projects:
                p_name = p.get("name", "Project")
                p_desc = p.get("description", "")
                techs = p.get("technologies", [])
                tech_str = ", ".join(techs) if techs else ""

                render_html(
                    f"""
                    <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.6rem;">
                        <div style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary);">{p_name}</div>
                        {f'<div style="font-size: 0.78rem; color: var(--accent); font-weight: 500; margin-top: 0.15rem;">Tech: {tech_str}</div>' if tech_str else ''}
                        <div style="font-size: 0.82rem; color: var(--text-secondary); margin-top: 0.35rem; line-height: 1.4;">{p_desc}</div>
                    </div>
                    """
                )
        else:
            st.caption("No projects extracted.")

    with col_exp:
        render_section_header("Experience & Education")
        experiences = parsed.get("experience", [])
        if experiences:
            render_html("<div style='font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase;'>Work History</div>")
            for exp in experiences:
                render_html(f"<div style='font-size: 0.84rem; color: var(--text-primary); margin-bottom: 0.25rem;'>• {exp}</div>")
        
        education = parsed.get("education", [])
        if education:
            render_html("<div style='font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); text-transform: uppercase; margin-top: 0.75rem;'>Education</div>")
            for edu in education:
                render_html(f"<div style='font-size: 0.84rem; color: var(--text-primary); margin-bottom: 0.25rem;'>• {edu}</div>")
