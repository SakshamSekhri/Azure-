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


def render_learning_plan_view():
    render_page_header(
        title="Your Personalized Improvement Plan",
        subtitle="A focused daily roadmap based on your target role, resume, and current skill gaps."
    )

    try:
        dash_data = api.get_dashboard_summary() or {}
    except Exception:
        dash_data = {}

    target_role = dash_data.get("target_role", "Target Role")
    target_company = dash_data.get("target_company")
    role_str = f"{target_role}" + (f" @ {target_company}" if target_company else "")
    if target_role and target_role != "Target Role":
        render_html(
            f"""
            <div style="margin-bottom: 1.25rem;">
                <span class="badge-role" style="font-size: 0.82rem; padding: 0.3rem 0.75rem;">
                    🎯 Target: <strong>{role_str}</strong>
                </span>
            </div>
            """
        )

    try:
        current_plan = api.get_current_plan()
    except Exception:
        current_plan = None

    try:
        imp_data = api.get_improvement_plan()
    except Exception:
        imp_data = None

    # -------------------------------------------------------------
    # 1. PLAN STATUS OVERVIEW & CONTROLS
    # -------------------------------------------------------------
    c_info, c_action = st.columns([2.6, 1.4])

    with c_info:
        if current_plan:
            acts = current_plan.get("activities", [])
            completed_count = sum(1 for a in acts if a.get("completed"))
            total_acts = len(acts) if acts else 7
            comp_pct = round((completed_count / total_acts * 100.0) if total_acts else 0.0, 1)

            render_html(
                f"""
                <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.2rem;">
                    Target Role: <span style="color: var(--accent);">{current_plan.get('target_role', 'Engineering Role')}</span>
                    &nbsp;|&nbsp; Completed: <strong>{completed_count} of {total_acts} Activities</strong> ({comp_pct}%)
                </div>
                """
            )
            render_progress_bar(comp_pct, height=7)
        else:
            st.info("No active 7-day curriculum generated yet. Click generate below to build your roadmap.")

    with c_action:
        with st.popover("⚙️ Plan Options", use_container_width=True):
            force = st.checkbox("Force fresh AI generation", value=False)
            if st.button("Generate 7-Day Plan", type="primary", use_container_width=True):
                with st.spinner("Synthesizing personalized curriculum..."):
                    try:
                        api.generate_plan(force_refresh=force)
                        st.success("Plan updated successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {str(e)}")

    st.markdown("---")

    # -------------------------------------------------------------
    # 2. SECTIONS: 7-DAY TIMELINE ROADMAP vs PRIORITY GAP ITEMS
    # -------------------------------------------------------------
    tab_timeline, tab_priority = st.tabs(["📅 7-Day Roadmap Timeline", "🎯 Priority Skill Benchmarks"])

    with tab_timeline:
        if not current_plan or not current_plan.get("activities"):
            render_empty_state(
                "No 7-Day Plan Available",
                "Generate a plan above to create your structured day-by-day learning roadmap.",
                icon="📅"
            )
        else:
            activities = current_plan.get("activities", [])
            activities.sort(key=lambda x: x.get("day_number", 1))

            render_section_header("Daily Preparation Roadmap")

            for act in activities:
                day_num = act.get("day_number", 1)
                topic = act.get("topic", "Topic")
                skill = act.get("skill_name", "Skill")
                is_done = act.get("completed", False)
                desc = act.get("resource_description", "")
                url = act.get("resource_url")
                act_id = act.get("id")

                status_badge = render_status_badge("Completed", "success") if is_done else render_status_badge(f"Day {day_num:02d}", "info")
                border_color = "#10B981" if is_done else "#6366F1"

                render_html(
                    f"""
                    <div style="background: var(--surface); border: 1px solid var(--border); border-left: 4px solid {border_color}; border-radius: 8px; padding: 1.1rem 1.3rem; margin-bottom: 0.85rem;">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.4rem;">
                            <div>
                                <span style="font-size: 0.72rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em;">DAY {day_num:02d}</span>
                                <h3 style="margin: 0.15rem 0; font-size: 1.05rem; font-weight: 600; color: var(--text-primary);">{topic} <span style="font-size: 0.86rem; font-weight: 500; color: var(--text-secondary);">({skill})</span></h3>
                            </div>
                            <div>{status_badge}</div>
                        </div>
                        <div style="font-size: 0.83rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 0.6rem;">
                            {desc}
                        </div>
                    </div>
                    """
                )

                col_btn1, col_btn2, col_chk, _ = st.columns([1.2, 1.2, 1.5, 2])
                with col_btn1:
                    if st.button("🎯 Practice", key=f"btn_prac_day_{day_num}_{act_id}", use_container_width=True):
                        st.session_state["focus_skill"] = skill
                        st.session_state["focus_topic"] = topic
                        st.session_state["pending_nav"] = "Skills & Topic Practice"
                        st.rerun()
                with col_btn2:
                    if st.button("📚 Learn", key=f"btn_learn_day_{day_num}_{act_id}", use_container_width=True):
                        st.session_state["rag_prefill_topic"] = topic
                        st.session_state["rag_prefill_query"] = f"Explain {topic} in {skill} with architectural patterns and interview concepts."
                        st.session_state["pending_nav"] = "RAG Assistant"
                        st.rerun()
                with col_chk:
                    checked = st.checkbox("Mark as completed", value=is_done, key=f"chk_done_{act_id}")
                    if checked != is_done:
                        try:
                            api.toggle_activity(act_id, checked)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error toggling activity: {e}")

                st.write("")

    with tab_priority:
        render_section_header("Dynamic Priority Competency Gaps", "Benchmarked dynamically to the 80% interview readiness target")
        if not imp_data or not imp_data.get("items"):
            render_empty_state("No Priority Gaps", "You have no outstanding competency gaps.", icon="🎯")
        else:
            items = imp_data.get("items", [])
            for it in items:
                skill_name = it.get("skill_name", "Skill")
                topic_name = it.get("topic_name", "Topic")
                curr = round(it.get("current_score", 0.0), 1)
                target = round(it.get("target_score", 80.0), 1)
                prio = it.get("priority", "MEDIUM")
                prio_badge = render_status_badge("High Priority", "danger") if prio == "HIGH" else (render_status_badge("Medium Priority", "warning") if prio == "MEDIUM" else render_status_badge("Low Priority", "neutral"))

                c_gap_info, c_gap_btn = st.columns([3, 1])
                with c_gap_info:
                    render_html(
                        f"""
                        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem 1.1rem; margin-bottom: 0.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                                <span style="font-weight: 600; font-size: 0.9rem; color: var(--text-primary);">{skill_name} — <span style="color: var(--text-secondary); font-weight: 500;">{topic_name}</span></span>
                                {prio_badge}
                            </div>
                            <div style="font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.35rem;">
                                <strong>Rationale:</strong> {it.get('reason', '')}
                            </div>
                            <div style="display: flex; gap: 1rem; font-size: 0.78rem; color: var(--text-muted); margin-bottom: 0.2rem;">
                                <span>Current: <strong>{curr}%</strong></span>
                                <span>Target: <strong>{target}%</strong></span>
                            </div>
                            <div class="saas-bar-track" style="height: 5px;">
                                <div class="saas-bar-fill" style="width: {min(100.0, curr)}%; background-color: {'#EF4444' if prio == 'HIGH' else '#F59E0B'};"></div>
                            </div>
                        </div>
                        """
                    )
                with c_gap_btn:
                    st.write("")
                    if st.button("Practice Topic →", key=f"btn_prio_prc_{it.get('id')}", use_container_width=True):
                        st.session_state["focus_skill"] = skill_name
                        st.session_state["focus_topic"] = topic_name
                        st.session_state["pending_nav"] = "Skills & Topic Practice"
                        st.rerun()
