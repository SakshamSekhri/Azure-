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


def render_job_view():
    render_page_header(
        title="Target Job Description",
        subtitle="Set your target career role, extract AI requirements, and benchmark directly against your profile."
    )

    try:
        latest_job = api.get_latest_job()
    except Exception:
        latest_job = None

    default_title = latest_job.get("title", "") if latest_job else ""
    default_company = latest_job.get("company", "") if latest_job else ""
    default_text = latest_job.get("raw_text", "") if latest_job else ""
    has_analysis = bool(latest_job and latest_job.get("parsed_data"))

    # 1. Main Job Setup Section
    render_html(
        f"""
        <div class="saas-panel">
            <div style="font-size: 0.72rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.2rem;">
                ACTIVE TARGET ROLE
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap;">
                <h2 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: var(--text-primary);">
                    {default_title or 'No Target Role Configured'}
                    <span style="color: var(--text-secondary); font-weight: 500; font-size: 1rem;">{f' @ {default_company}' if default_company else ''}</span>
                </h2>
                <span style="font-size: 0.8rem; color: #10B981; font-weight: 600;">{'✓ Analyzed with Azure AI' if has_analysis else 'Pending Analysis'}</span>
            </div>
        </div>
        """
    )

    with st.expander("📝 Edit Role Details or Paste Job Description", expanded=not has_analysis):
        c_title, c_comp = st.columns([2.5, 1.5])
        with c_title:
            job_title = st.text_input("Target Job Title", value=default_title, placeholder="e.g. Senior Backend Engineer")
        with c_comp:
            company_name = st.text_input("Target Company (Optional)", value=default_company, placeholder="e.g. Microsoft")

        jd_text = st.text_area(
            "Job Description Text",
            value=default_text,
            height=180,
            placeholder="Paste role requirements, tech stack, qualifications, and responsibilities here..."
        )

        c_sub, c_force = st.columns([2, 2])
        with c_sub:
            analyze_clicked = st.button("🔍 Save & Analyze Role with Azure AI", type="primary", use_container_width=True)
        with c_force:
            force_refresh = st.checkbox("Force fresh re-analysis", value=False)

        if analyze_clicked:
            if not job_title or len(jd_text.strip()) < 20:
                st.error("Please provide a valid Job Title and at least 20 characters of Job Description text.")
            else:
                with st.spinner("Analyzing requirements via Azure AI Foundry..."):
                    try:
                        if not latest_job or latest_job.get("raw_text") != jd_text.strip() or latest_job.get("title") != job_title.strip():
                            new_job = api.create_job(job_title.strip(), jd_text.strip(), company_name.strip() if company_name else None)
                            job_id = new_job["id"]
                        else:
                            job_id = latest_job["id"]

                        api.analyze_job(job_id, force_refresh=force_refresh)
                        st.success("Target Job successfully analyzed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")

    if not has_analysis:
        return

    parsed = latest_job["parsed_data"]
    st.markdown("---")

    # -------------------------------------------------------------
    # 2. EXTRACTED INTELLIGENCE & ROLE ALIGNMENT
    # -------------------------------------------------------------
    # Candidate vs JD Alignment
    try:
        cand_jd = api.get_candidate_vs_jd()
    except Exception:
        cand_jd = {}

    if cand_jd:
        coverage = cand_jd.get("match_percentage", 0.0)
        render_html(
            f"""
            <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.25rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                    <span style="font-weight: 600; font-size: 0.92rem; color: var(--text-primary);">Candidate Skill Alignment</span>
                    <span style="font-weight: 700; font-size: 1.1rem; color: {'#10B981' if coverage >= 75 else '#6366F1'};">{coverage}% Coverage</span>
                </div>
                <div class="saas-bar-track" style="height: 6px;">
                    <div class="saas-bar-fill" style="width: {min(100.0, coverage)}%; background-color: {'#10B981' if coverage >= 75 else '#6366F1'};"></div>
                </div>
            </div>
            """
        )

    # Role Expectations
    exp = parsed.get("role_expectations")
    req_exp = parsed.get("experience_required")
    if exp or req_exp:
        render_section_header("Role Expectations & Scope")
        if exp:
            render_html(f"<div style='font-size: 0.86rem; color: var(--text-primary); line-height: 1.5; margin-bottom: 0.35rem;'>{exp}</div>")
        if req_exp:
            st.caption(f"Experience Requirement: **{req_exp}**")
        st.write("")

    # Skills Breakdown: Required vs Preferred
    col_req, col_pref = st.columns(2)
    with col_req:
        render_section_header("Mandatory Required Skills")
        req_skills = parsed.get("required_skills", [])
        if req_skills:
            req_html = []
            for r in req_skills:
                req_html.append(
                    f"<span class='status-badge badge-danger' style='margin-right: 0.35rem; margin-bottom: 0.35rem;'>"
                    f"<strong>{r.get('name')}</strong> ({r.get('category')})</span>"
                )
            render_html(f"<div style='display: flex; flex-wrap: wrap;'>{''.join(req_html)}</div>")
        else:
            st.caption("None extracted.")

    with col_pref:
        render_section_header("Preferred / Bonus Skills")
        pref_skills = parsed.get("preferred_skills", [])
        if pref_skills:
            pref_html = []
            for p in pref_skills:
                pref_html.append(
                    f"<span class='status-badge badge-warning' style='margin-right: 0.35rem; margin-bottom: 0.35rem;'>"
                    f"<strong>{p.get('name')}</strong> ({p.get('category')})</span>"
                )
            render_html(f"<div style='display: flex; flex-wrap: wrap;'>{''.join(pref_html)}</div>")
        else:
            st.caption("None extracted.")

    st.write("")

    # Key Assessment Topics & Responsibilities
    col_topics, col_resp = st.columns(2)
    with col_topics:
        render_section_header("Key Assessment Focus Areas")
        areas = parsed.get("assessment_areas", [])
        if areas:
            for a in areas:
                render_html(f"<div style='font-size: 0.84rem; color: #334155; margin-bottom: 0.25rem;'>• {a}</div>")
        else:
            st.caption("None specified.")

    with col_resp:
        render_section_header("Core Responsibilities")
        resps = parsed.get("key_responsibilities", [])
        if resps:
            for r in resps:
                render_html(f"<div style='font-size: 0.84rem; color: #334155; margin-bottom: 0.25rem;'>• {r}</div>")
        else:
            st.caption("None specified.")
