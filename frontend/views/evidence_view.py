import streamlit as st
from frontend.components.api_client import api


def render_evidence_view():
    st.markdown("### 🗂️ Collected Evidence Repository")
    st.markdown("All empirical evidence supporting your claimed competencies across resumes, GitHub, objective assessments, and project artifacts.")

    try:
        evidences = api.list_evidence()
    except Exception as e:
        st.error(f"Failed to load evidence: {str(e)}")
        return

    if not evidences:
        st.info("No evidence records collected yet. Upload a resume, connect GitHub, or take an assessment to accumulate evidence.")
        return

    # Filter by type
    types = ["All"] + sorted(list(set(e.get("type", "General") for e in evidences)))
    selected_type = st.selectbox("Filter Evidence by Type", types)

    filtered = evidences if selected_type == "All" else [e for e in evidences if e.get("type") == selected_type]

    st.markdown(f"Displaying **{len(filtered)}** verified evidence records:")

    for ev in filtered:
        ev_type = ev.get("type", "General")
        badge_type = "badge-info" if ev_type == "Resume" else ("badge-high" if ev_type == "GitHub" else "badge-medium")
        strength = ev.get("evidence_strength", 0.5)

        with st.expander(f"[{ev_type}] {ev.get('title')} (Strength: {int(strength*100)}%)"):
            st.write(ev.get("description") or "No description.")
            st.caption(f"Source: `{ev.get('source')}` | Created: {ev.get('created_at')}")
            if ev.get("url"):
                st.markdown(f"🔗 [Link Reference]({ev.get('url')})")
            if ev.get("skill_name"):
                st.markdown(f"Mapped Skill: **{ev.get('skill_name')}**")
