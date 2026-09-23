import streamlit as st
from frontend.components.api_client import api
from frontend.components.ui import (
    render_page_header,
    render_section_header,
    render_progress_bar,
    render_status_badge,
    render_empty_state,
    render_styled_table,
    render_html
)


def render_skills_matrix_view():
    render_page_header(
        title="Skills Gaps & Readiness",
        subtitle="Visual diagnostic breakdown of verified competencies, categorized readiness, and critical placement gaps."
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
        cand_jd = api.get_candidate_vs_jd()
    except Exception:
        cand_jd = {}

    try:
        matrix = api.get_skill_matrix()
    except Exception as e:
        render_empty_state("Skill Matrix Unavailable", f"Could not load skill matrix: {str(e)}", icon="⚠️")
        return

    if not matrix:
        render_empty_state(
            "No Skills Tracked Yet",
            "Upload your resume or set a target job description to begin tracking your skills and readiness.",
            icon="🧩"
        )
        return

    # -------------------------------------------------------------
    # 1. READINESS OVERVIEW ROW
    # -------------------------------------------------------------
    overall_readiness = round(dash_data.get("overall_preparation_score", 0.0), 1)
    target_role = dash_data.get("target_role", "Target Role")
    target_company = dash_data.get("target_company")
    role_str = f"{target_role}" + (f" @ {target_company}" if target_company else "")

    verified_count = sum(1 for s in matrix if s.get("assessment_score") is not None)
    total_skills = len(matrix)
    
    missing_names = set(cand_jd.get("skill_gaps", []) if cand_jd else [])
    critical_gaps = [
        s for s in matrix
        if s.get("status") in ("Weak", "Critical Gap", "Missing", "Required Missing")
        or s.get("skill_name") in missing_names
        or (s.get("assessment_score") is not None and s.get("assessment_score") < 60.0)
    ]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Overall Readiness", f"{overall_readiness}%", help="Synthesized readiness across technical assessments and role requirements")
    with c2:
        st.metric("Target Benchmark", "80.0%", help="Target threshold required for interview readiness")
    with c3:
        st.metric("Verified Skills", f"{verified_count} / {total_skills}", help="Skills assessed via dynamic MCQs")
    with c4:
        st.metric("Critical Gaps", len(critical_gaps), help="Required skills below 60% or missing")

    st.caption(f"Evaluated against target: **{role_str}**")
    st.markdown("---")

    # -------------------------------------------------------------
    # 2. TWO CLEAN VIEWS: CATEGORIZED READINESS vs WHAT AM I MISSING?
    # -------------------------------------------------------------
    tab_readiness, tab_gaps, tab_all = st.tabs([
        "📊 Skill Readiness by Category",
        "🎯 What Am I Missing? (Gaps Analysis)",
        "📋 Complete Tracking Matrix"
    ])

    # TAB 1: CATEGORIZED READINESS WITH INLINE PROGRESS BARS
    with tab_readiness:
        render_section_header("Competencies by Technical Domain")
        
        categories = {}
        for m in matrix:
            cat = m.get("category", "General") or "General"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(m)

        for cat_name, cat_skills in sorted(categories.items()):
            render_html(
                f"""
                <div style="font-size: 0.95rem; font-weight: 600; color: var(--text-primary); margin-top: 1rem; margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between;">
                    <span>{cat_name}</span>
                    <span style="font-size: 0.76rem; color: var(--text-secondary); font-weight: 500;">{len(cat_skills)} competencies</span>
                </div>
                """
            )

            cols = st.columns(2)
            for idx, s in enumerate(cat_skills):
                col = cols[idx % 2]
                with col:
                    s_name = s.get("skill_name", "Skill")
                    score_val = s.get("assessment_score")
                    
                    if score_val is not None:
                        score_num = round(score_val, 1)
                        if score_num >= 80.0:
                            badge_html = render_status_badge("Strong", "success")
                            bar_color = "#10B981"
                        elif score_num >= 60.0:
                            badge_html = render_status_badge("Needs Attention", "warning")
                            bar_color = "#F59E0B"
                        else:
                            badge_html = render_status_badge("Critical", "danger")
                            bar_color = "#EF4444"
                        score_text = f"{score_num}%"
                    else:
                        score_num = 0.0
                        score_text = "Unassessed"
                        badge_html = render_status_badge("Unverified", "info") if (s.get("claimed") or s.get("github_evidence")) else render_status_badge("Missing", "neutral")
                        bar_color = "#CBD5E1"

                    render_html(
                        f"""
                        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 0.9rem; margin-bottom: 0.55rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                                <span style="font-weight: 600; font-size: 0.85rem; color: var(--text-primary);">{s_name}</span>
                                <div>
                                    <span style="font-weight: 600; font-size: 0.82rem; color: var(--text-secondary); margin-right: 0.35rem;">{score_text}</span>
                                    {badge_html}
                                </div>
                            </div>
                            <div class="saas-bar-track" style="height: 5px;">
                                <div class="saas-bar-fill" style="width: {min(100.0, score_num)}%; background-color: {bar_color};"></div>
                            </div>
                        </div>
                        """
                    )

    # TAB 2: WHAT AM I MISSING? (CRITICAL GAPS)
    with tab_gaps:
        render_section_header("Critical Missing Skills & Gaps", "Target role requirements where your current level is below 80%")
        
        target_benchmark = 80.0
        gap_items = []
        for s in matrix:
            s_name = s.get("skill_name")
            score_val = s.get("assessment_score")
            status_str = (s.get("status") or "").lower()
            
            curr = round(score_val, 1) if score_val is not None else 0.0
            gap = max(0.0, target_benchmark - curr)
            
            is_critical = status_str in ("weak", "critical gap", "missing", "required missing") or s_name in missing_names or curr < 50.0
            is_medium = (curr >= 50.0 and curr < 80.0) or status_str in ("developing",)
            
            if is_critical:
                priority = "HIGH"
            elif is_medium:
                priority = "MEDIUM"
            else:
                continue

            gap_items.append({
                "skill_name": s_name,
                "current": curr,
                "target": target_benchmark,
                "gap": round(gap, 1),
                "priority": priority,
                "is_unassessed": (score_val is None)
            })

        gap_items.sort(key=lambda x: (0 if x["priority"] == "HIGH" else 1, -x["gap"]))

        if gap_items:
            for item in gap_items:
                p_badge = render_status_badge("High Priority", "danger") if item["priority"] == "HIGH" else render_status_badge("Medium Priority", "warning")
                curr_display = f"{item['current']}%" if not item["is_unassessed"] else "0% (Unassessed)"
                
                c_info, c_action = st.columns([3, 1])
                with c_info:
                    render_html(
                        f"""
                        <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem 1rem; margin-bottom: 0.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                                <span style="font-weight: 600; font-size: 0.92rem; color: var(--text-primary);">{item['skill_name']}</span>
                                {p_badge}
                            </div>
                            <div style="display: flex; gap: 1.5rem; font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 0.4rem;">
                                <span>Current: <strong style="color: var(--text-primary);">{curr_display}</strong></span>
                                <span>Target: <strong style="color: var(--text-primary);">{item['target']}%</strong></span>
                                <span>Gap: <strong style="color: {'#EF4444' if item['gap'] > 30 else '#F59E0B'};">+{item['gap']}%</strong></span>
                            </div>
                            <div class="saas-bar-track" style="height: 6px;">
                                <div class="saas-bar-fill" style="width: {min(100.0, item['current'])}%; background-color: {'#EF4444' if item['priority'] == 'HIGH' else '#F59E0B'};"></div>
                            </div>
                        </div>
                        """
                    )
                with c_action:
                    st.write("")
                    if st.button("Practice Skill →", key=f"btn_gap_prc_{item['skill_name']}", use_container_width=True):
                        st.session_state["focus_skill"] = item['skill_name']
                        st.session_state["pending_nav"] = "Skills & Topic Practice"
                        st.rerun()
        else:
            st.success("✓ No skill gaps identified! You meet or exceed the 80% benchmark across all tracked skills.")

    # TAB 3: COMPLETE TRACKING MATRIX (CLEAN TABLE)
    with tab_all:
        render_section_header("Multi-Source Evidence Matrix")
        headers = ["Skill", "Category", "Resume Claim", "GitHub Proof", "Assessment Score", "Confidence", "Status"]
        rows = []
        for item in matrix:
            conf = item.get("confidence", "Low")
            conf_badge = render_status_badge(conf, "success" if conf == "High" else ("warning" if conf == "Medium" else "neutral"))
            claimed_str = "✓ Yes" if item.get("claimed") else "—"
            github_str = "✓ Yes" if item.get("github_evidence") else "—"
            score_val = item.get("assessment_score")
            score_str = f"<strong>{score_val}%</strong>" if score_val is not None else "<span style='color:#94A3B8;'>Unassessed</span>"

            rows.append([
                f"<strong>{item.get('skill_name')}</strong>",
                item.get("category", "General"),
                claimed_str,
                github_str,
                score_str,
                conf_badge,
                item.get("status", "N/A")
            ])
        render_styled_table(headers, rows)
