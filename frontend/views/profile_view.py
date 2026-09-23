import streamlit as st
from frontend.components.api_client import api


def render_profile_view():
    st.markdown("### 👤 Student Profile & Target Role")
    st.markdown("Manage your academic details, target career track, and linked public profiles.")

    try:
        profile = api.get_profile()
    except Exception as e:
        st.error(f"Error loading profile: {str(e)}")
        return

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name", value=profile.get("name", ""))
            college = st.text_input("College / University", value=profile.get("college", ""))
            degree = st.text_input("Degree Program", value=profile.get("degree", ""))

        with col2:
            active_job = profile.get("active_job")
            if active_job and active_job.get("title"):
                role_display = f"{active_job.get('title')}" + (f" @ {active_job.get('company')}" if active_job.get('company') else "")
            else:
                role_display = profile.get("target_role") or "No active target job linked"

            st.text_input(
                "Active Target Role",
                value=role_display,
                disabled=True,
                help="Your Target Job is the single source of truth for your evaluation role. Manage it in the Target Job page."
            )

            exp_levels = ["Entry Level", "1-2 Years", "3-5 Years"]
            current_exp = profile.get("experience_level", "Entry Level")
            exp_index = exp_levels.index(current_exp) if current_exp in exp_levels else 0
            experience_level = st.selectbox("Experience Level", exp_levels, index=exp_index)

            grad_year = st.number_input("Graduation Year", min_value=2020, max_value=2032, value=int(profile.get("graduation_year") or 2026))

        github_username = st.text_input("GitHub Username", value=profile.get("github_username", "") or "", help="Public GitHub handle for evidence extraction")

        submitted = st.form_submit_button("Save Profile Updates", type="primary", use_container_width=True)
        if submitted:
            try:
                update_payload = {
                    "name": name,
                    "college": college,
                    "degree": degree,
                    "graduation_year": int(grad_year),
                    "experience_level": experience_level,
                    "github_username": github_username
                }
                if active_job and active_job.get("title"):
                    update_payload["target_role"] = active_job.get("title")
                api.update_profile(update_payload)
                st.success("Profile saved successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update profile: {str(e)}")
