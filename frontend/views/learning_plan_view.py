import streamlit as st
from frontend.components.api_client import api


def render_learning_plan_view():
    st.markdown("### 📅 Personalized 7-Day Learning Curriculum")
    st.markdown("A customized study roadmap generated from your identified skill gaps and assessment performance.")
    st.markdown("<span class='credit-pill'>💡 Credit Control: One AI request generated on click, stored and tracked day-by-day</span>", unsafe_allow_html=True)

    col_gen, col_force = st.columns([2, 1])
    with col_gen:
        if st.button("🚀 Generate 7-Day Learning Plan", type="primary", use_container_width=True):
            with st.spinner("Synthesizing personalized curriculum based on your skill gaps..."):
                try:
                    plan = api.generate_plan()
                    st.success("7-Day Learning Plan generated and activated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to generate plan: {str(e)}")

    with col_force:
        force = st.checkbox("Force new generation", key="force_plan")
        if force:
            if st.button("Regenerate Plan", use_container_width=True):
                with st.spinner("Regenerating curriculum..."):
                    try:
                        api.generate_plan(force_refresh=True)
                        st.success("Plan regenerated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    st.markdown("---")

    # Display Active Plan
    try:
        current_plan = api.get_current_plan()
    except Exception as e:
        st.error(f"Failed to load plan: {str(e)}")
        return

    if not current_plan:
        st.info("No active learning plan. Click 'Generate 7-Day Learning Plan' to synthesize your schedule.")
        return

    # Plan Summary Header
    st.markdown(f"#### 🎯 Track: **{current_plan.get('target_role')}** (7 Days)")
    st.markdown(f"*{current_plan.get('summary', '')}*")

    pct = current_plan.get("completion_percentage", 0.0)
    st.progress(pct / 100.0, text=f"Curriculum Completion: {pct}%")

    st.write("")

    # Activities Day by Day
    activities = current_plan.get("activities", [])
    days_dict = {}
    for a in activities:
        d = a.get("day_number", 1)
        if d not in days_dict:
            days_dict[d] = []
        days_dict[d].append(a)

    for day_num in sorted(days_dict.keys()):
        day_acts = days_dict[day_num]
        all_done = all(a.get("completed") for a in day_acts)
        status_badge = "🟢 Completed" if all_done else "🟡 Pending"

        with st.expander(f"Day {day_num}: {day_acts[0].get('topic')} — {status_badge}", expanded=(not all_done)):
            for act in day_acts:
                col_check, col_details = st.columns([1, 10])
                with col_check:
                    is_completed = st.checkbox(
                        "Done",
                        value=act.get("completed", False),
                        key=f"act_{act.get('id')}",
                        label_visibility="collapsed"
                    )
                    if is_completed != act.get("completed"):
                        api.toggle_activity(act.get("id"), is_completed)
                        st.rerun()

                with col_details:
                    st.markdown(f"**{act.get('topic')}** (`{act.get('skill_name')}` | Type: *{act.get('activity_type')}*)")
                    st.write(act.get("resource_description", ""))
                    if act.get("resource_url"):
                        st.markdown(f"🔗 [Recommended Resource Docs]({act.get('resource_url')})")
                st.write("")
