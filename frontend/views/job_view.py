import streamlit as st
from frontend.components.api_client import api


def render_job_view():
    st.markdown("### 🎯 Target Job Description (JD) Processing")
    st.markdown("Enter a target job posting to extract required technical qualifications and benchmark your skills.")
    st.markdown("<span class='credit-pill'>💡 Credit Control: AI is ONLY invoked when you explicitly click 'Analyze Job Description'</span>", unsafe_allow_html=True)

    tab_input, tab_active = st.tabs(["📝 Add New Job Description", "📋 Active Job Analysis"])

    with tab_input:
        with st.form("job_form"):
            title = st.text_input("Job Title / Role", placeholder="Senior Backend Software Engineer")
            company = st.text_input("Company Name (Optional)", placeholder="Microsoft / Stripe / StartUp")
            raw_text = st.text_area("Job Description Content", height=220, placeholder="Paste requirements, tech stack, and responsibilities here...")
            submitted = st.form_submit_button("Save Job Description", type="primary", use_container_width=True)

            if submitted:
                if not title or len(raw_text.strip()) < 20:
                    st.error("Please provide a title and at least 20 characters of JD text.")
                else:
                    try:
                        job = api.create_job(title, raw_text, company)
                        st.success(f"Job Description for '{title}' saved successfully! Switch to the Active tab to analyze.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to save JD: {str(e)}")

    with tab_active:
        try:
            latest_job = api.get_latest_job()
        except Exception:
            latest_job = None

        if not latest_job:
            st.info("No job description saved yet. Add one in the 'Add New Job Description' tab.")
            return

        st.markdown(f"#### Active Target: **{latest_job.get('title')}** ({latest_job.get('company') or 'Tech Enterprise'})")
        
        force = st.checkbox("Force re-analysis (bypass AI cache)", key="force_jd")
        if st.button("🔍 Analyze Job Description with AI", type="primary"):
            with st.spinner("Analyzing JD requirements via Azure Foundry Agent..."):
                try:
                    res = api.analyze_job(latest_job["id"], force_refresh=force)
                    st.success("Job Description analyzed! Required skills mapped to your gap matrix.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Analysis failed: {str(e)}")

        parsed = latest_job.get("parsed_data")
        if parsed:
            st.markdown("---")
            st.markdown(f"**Role Expectations:** {parsed.get('role_expectations', 'N/A')}")
            st.markdown(f"**Experience Requirement:** {parsed.get('experience_required', 'N/A')}")

            col_req, col_pref = st.columns(2)
            with col_req:
                st.markdown("##### 🔴 Mandatory Required Skills")
                for r in parsed.get("required_skills", []):
                    st.markdown(f"<span class='metric-badge badge-low'>{r.get('name')} ({r.get('category')})</span>", unsafe_allow_html=True)

            with col_pref:
                st.markdown("##### 🟡 Preferred / Bonus Skills")
                for p in parsed.get("preferred_skills", []):
                    st.markdown(f"<span class='metric-badge badge-medium'>{p.get('name')} ({p.get('category')})</span>", unsafe_allow_html=True)

            st.markdown("##### 📋 Key Responsibilities")
            for resp in parsed.get("key_responsibilities", []):
                st.markdown(f"- {resp}")
        else:
            st.warning("This JD has not been analyzed yet. Click 'Analyze Job Description with AI'.")
            with st.expander("View Raw JD Text"):
                st.text_area("Content", value=latest_job.get("raw_text", ""), height=200, disabled=True)
