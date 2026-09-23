from datetime import datetime
import streamlit as st
from frontend.components.api_client import api
from frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_progress_bar,
    render_status_badge,
    render_styled_table,
    render_empty_state,
    render_html
)


def render_dashboard_view():
    user = st.session_state.get("user_info") or {}
    user_name = user.get("name") or (user.get("email", "").split("@")[0].capitalize() if user.get("email") else "Candidate")
    
    current_hour = datetime.now().hour
    greeting = "Good morning" if current_hour < 12 else ("Good afternoon" if current_hour < 18 else "Good evening")

    render_page_header(
        title=f"{greeting}, {user_name}",
        subtitle="Your placement preparation at a glance."
    )

    try:
        data = api.get_dashboard_summary()
    except Exception as e:
        render_empty_state("Unable to Load Dashboard", f"Error connecting to backend services: {str(e)}", icon="⚠️")
        return

    readiness_score = round(data.get("overall_preparation_score", 0.0), 1)
    target_role = data.get("target_role") or "Target Role"
    target_company = data.get("target_company")
    company_str = f" @ {target_company}" if target_company else ""

    matrix = data.get("skill_matrix", [])
    weak_skills = [
        s for s in matrix
        if s.get("status") in ("Weak", "Critical Gap", "Missing", "Required Missing")
        or (s.get("assessment_score") is not None and s.get("assessment_score") < 65.0)
    ]
    attention_count = len(weak_skills)

    # -------------------------------------------------------------
    # 1. PROMINENT TARGET ROLE & READINESS HERO SECTION
    # -------------------------------------------------------------
    render_html(
        f"""
        <div class="saas-panel" style="padding: 1.5rem 1.8rem; margin-bottom: 1.5rem; border-left: 4px solid var(--accent);">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
                <div style="flex: 1; min-width: 260px;">
                    <div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 0.2rem;">
                        TARGET ROLE & BENCHMARK
                    </div>
                    <div style="font-size: 1.25rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.75rem;">
                        {target_role}<span style="color: var(--text-secondary); font-weight: 500;">{company_str}</span>
                    </div>
                    <div style="display: flex; align-items: baseline; gap: 0.6rem; margin-bottom: 0.4rem;">
                        <span style="font-size: 0.86rem; color: var(--text-secondary); font-weight: 500;">Placement Readiness:</span>
                        <span style="font-size: 1.75rem; font-weight: 700; color: var(--text-primary); letter-spacing: -0.02em;">{readiness_score}%</span>
                        <span style="font-size: 0.78rem; color: var(--text-muted);">(Target: 80%)</span>
                    </div>
                    <div style="max-width: 480px; margin-bottom: 0.5rem;">
                        <div class="saas-bar-track" style="height: 7px;">
                            <div class="saas-bar-fill" style="width: {min(100.0, readiness_score)}%; background-color: {'#10B981' if readiness_score >= 80 else ('#6366F1' if readiness_score >= 60 else '#F59E0B')};"></div>
                        </div>
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary);">
                        {'⚡ Ready for interview rounds!' if readiness_score >= 80 else f'⚠️ <strong>{attention_count} areas</strong> need attention before target benchmark.'}
                    </div>
                </div>
            </div>
        </div>
        """
    )

    # -------------------------------------------------------------
    # 2. KEY METRICS (Concise, Clean Row)
    # -------------------------------------------------------------
    tech_knowledge = round(data.get("technical_knowledge_percentage", 0.0), 1)
    resume_match = round(data.get("resume_match_percentage", 0.0), 1)
    jd_coverage = round(data.get("jd_coverage_percentage", 0.0), 1)
    plan_progress = round(data.get("active_plan_progress_percentage", 0.0), 1)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Technical Knowledge", f"{tech_knowledge}%", help="Average verified MCQ test score")
    with m2:
        st.metric("Resume Match", f"{resume_match}%", help="Claimed skills compared to Job Description")
    with m3:
        st.metric("Job Coverage", f"{jd_coverage}%", help="Percentage of mandatory competencies addressed")
    with m4:
        st.metric("Plan Progress", f"{plan_progress}%", help="Completion percentage of active 7-day curriculum")

    st.write("")

    # -------------------------------------------------------------
    # 3. SPLIT ROW: YOUR FOCUS vs CONTINUE PREPARATION
    # -------------------------------------------------------------
    col_focus, col_action = st.columns([1.1, 1.2])

    with col_focus:
        render_section_header("🎯 Your Focus", "Areas requiring immediate practice to raise overall readiness")
        
        top_focus = weak_skills[:4]
        if top_focus:
            for s in top_focus:
                s_name = s.get("skill_name", "Skill")
                score_val = s.get("assessment_score")
                if score_val is not None:
                    score_num = round(score_val, 1)
                    score_display = f"{score_num}%"
                else:
                    score_num = 0.0
                    score_display = "Unassessed"

                render_html(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.84rem; margin-top: 0.6rem; margin-bottom: 0.2rem;">
                        <span style="font-weight: 600; color: var(--text-primary);">{s_name}</span>
                        <span style="color: {'#EF4444' if score_num < 50 else '#F59E0B'}; font-weight: 600;">{score_display}</span>
                    </div>
                    """
                )
                render_progress_bar(score_num, height=5)
            
            st.write("")
            if st.button("View All Skill Gaps & Readiness →", use_container_width=True):
                st.session_state["pending_nav"] = "Skills Gaps & Readiness"
                st.rerun()
        else:
            st.success("✓ All evaluated skills are currently meeting or exceeding targets!")

    with col_action:
        render_section_header("⚡ Continue Preparation", "Next recommended task deterministically prioritized for you")
        rec = data.get("recommended_action", {})
        action_type = rec.get("action_type", "").upper()

        if action_type in ("PRACTICE", "FOCUSED_ASSESSMENT"):
            target_nav_page = "Skills & Topic Practice"
        elif action_type == "RESUME":
            target_nav_page = "Resume / CV"
        elif action_type in ("IMPROVEMENT_PLAN", "LEARNING"):
            target_nav_page = "Personalized Improvement Plan"
        elif action_type == "ASSESSMENT":
            target_nav_page = "Personalized Assessment"
        elif action_type == "JOB":
            target_nav_page = "Target Job"
        else:
            target_nav_page = "Skills & Topic Practice"

        render_html(
            f"""
            <div class="saas-panel" style="margin-bottom: 0.75rem;">
                <div style="font-size: 0.72rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;">
                    RECOMMENDED TASK
                </div>
                <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.4rem;">
                    {rec.get('title', 'Adaptive Practice Session')}
                </div>
                <div style="font-size: 0.84rem; color: var(--text-secondary); margin-bottom: 0.45rem;">
                    <strong>Why:</strong> {rec.get('reason', 'Targeted reinforcement for placement readiness')}
                </div>
                <div style="font-size: 0.8rem; color: var(--text-muted); line-height: 1.4;">
                    {rec.get('description', '')}
                </div>
            </div>
            """
        )

        btn_label = f"Start: {rec.get('title', 'Continue')[:28]} →"
        if st.button(btn_label, type="primary", use_container_width=True, key="dashboard_continue_btn"):
            if rec.get("skill_name"):
                st.session_state["focus_skill"] = rec.get("skill_name")
            if rec.get("topic"):
                st.session_state["focus_topic"] = rec.get("topic")
            st.session_state["pending_nav"] = target_nav_page
            st.rerun()

    st.write("")
    st.markdown("---")

    # -------------------------------------------------------------
    # 4. RECENT ACTIVITY (Clean Pure-CSS Tables, Zero Iframes)
    # -------------------------------------------------------------
    render_section_header("📜 Recent Activity", "Track your latest assessments and practice milestones")
    
    col_asm, col_prac = st.columns(2)
    with col_asm:
        render_html("<div style='font-size: 0.88rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.4rem;'>Recent Assessments</div>")
        recent_assessments = data.get("recent_assessment_results", [])
        if recent_assessments:
            headers = ["Role / Assessment", "Date", "Score", "Result"]
            rows = []
            for asm in recent_assessments[:5]:
                passed = asm.get("passed", False)
                status_html = render_status_badge("Passed", "success") if passed else render_status_badge("Review", "warning")
                score_str = f"<strong>{asm.get('score_percentage', 0.0)}%</strong> ({asm.get('correct_count')}/{asm.get('total_questions')})"
                rows.append([
                    f"<strong>{asm.get('role', 'Assessment')}</strong>",
                    asm.get("completed_at", "N/A"),
                    score_str,
                    status_html
                ])
            render_styled_table(headers, rows)
        else:
            st.caption("No assessments completed yet. Take an assessment to record your verified baseline.")

    with col_prac:
        render_html("<div style='font-size: 0.88rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.4rem;'>Recent Practice Sessions</div>")
        recent_practice = data.get("recent_practice_results", [])
        if recent_practice:
            headers = ["Skill", "Topic", "Date", "Score"]
            rows = []
            for prac in recent_practice[:5]:
                score_val = prac.get("score_percentage", 0.0)
                badge_type = "success" if score_val >= 80.0 else ("warning" if score_val >= 60.0 else "danger")
                score_badge = render_status_badge(f"{score_val}%", badge_type)
                rows.append([
                    f"<strong>{prac.get('skill', 'General')}</strong>",
                    prac.get("topic", "Core"),
                    prac.get("completed_at", "N/A"),
                    score_badge
                ])
            render_styled_table(headers, rows)
        else:
            st.caption("No practice sessions completed yet. Practice weak topics to build mastery.")
