import streamlit as st
import streamlit.components.v1 as components
from frontend.components.api_client import api

TABLE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* { font-family: 'Inter', sans-serif; box-sizing: border-box; }
.styled-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.styled-table th { background-color: #f8fafc; border-bottom: 2px solid #e2e8f0; text-align: left; padding: 0.75rem; font-weight: 600; color: #475569; }
.styled-table td { padding: 0.75rem; border-bottom: 1px solid #e2e8f0; color: #1e293b; }
.styled-table tr:hover td { background-color: #f8fafc; }
.metric-badge { display: inline-block; font-size: 0.78rem; font-weight: 600; padding: 0.2rem 0.55rem; border-radius: 9999px; }
.badge-high   { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.badge-medium { background: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }
.badge-low    { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.badge-info   { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
code { background: #f1f5f9; border-radius: 4px; padding: 0.15rem 0.4rem; font-size: 0.8rem; color: #0f172a; }
</style>
"""


def render_dashboard_view():
    st.markdown("### 📊 Student Preparation Command Center")
    st.markdown("Real-time readiness analytics synthesized from verified evidence, objective scoring, and dynamic assessments.")

    try:
        data = api.get_dashboard_summary()
    except Exception as e:
        st.error(f"Failed to load dashboard: {str(e)}")
        return

    # Top Welcome & Next Action Banner
    rec = data.get("recommended_action", {})
    st.markdown(f"""
    <div class="action-banner">
        <h4>⚡ Recommended Next Action: {rec.get('title', 'Continue Preparation')}</h4>
        <p><strong>Why:</strong> {rec.get('reason', 'Step-by-step verified preparation')}</p>
        <p style="margin-top: 0.3rem; opacity: 0.9;">{rec.get('description', '')}</p>
    </div>
    """, unsafe_allow_html=True)

    # 4 Key Metrics Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="app-card">
            <span style="color: #64748b; font-size: 0.85rem; font-weight: 500;">Overall Preparation</span>
            <h2 style="margin: 0.3rem 0; color: #1e293b;">{data.get('overall_preparation_score', 0)}%</h2>
            <div style="font-size: 0.8rem; color: #22c55e;">Target: {data.get('target_role', 'Engineer')}</div>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="app-card">
            <span style="color: #64748b; font-size: 0.85rem; font-weight: 500;">Assessed Skills</span>
            <h2 style="margin: 0.3rem 0; color: #1e293b;">{data.get('assessed_skills_count', 0)} / {data.get('total_skills_tracked', 0)}</h2>
            <div style="font-size: 0.8rem; color: #3b82f6;">Objective MCQ verified</div>
        </div>
        """, unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="app-card">
            <span style="color: #64748b; font-size: 0.85rem; font-weight: 500;">Evidence Items</span>
            <h2 style="margin: 0.3rem 0; color: #1e293b;">{data.get('evidence_count', 0)}</h2>
            <div style="font-size: 0.8rem; color: #0284c7;">{'GitHub Connected ✓' if data.get('github_connected') else 'GitHub Not Linked'}</div>
        </div>
        """, unsafe_allow_html=True)

    with c4:
        st.markdown(f"""
        <div class="app-card">
            <span style="color: #64748b; font-size: 0.85rem; font-weight: 500;">7-Day Plan Progress</span>
            <h2 style="margin: 0.3rem 0; color: #1e293b;">{data.get('active_plan_progress_percentage', 0)}%</h2>
            <div style="font-size: 0.8rem; color: #eab308;">{'Active Plan In Progress' if data.get('has_active_plan') else 'No Active Plan'}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Strengths vs Gaps Row
    col_str, col_gap = st.columns(2)
    with col_str:
        st.markdown("##### 🏆 Verified Strengths (High Confidence)")
        strengths = data.get("top_strengths", [])
        if strengths:
            for s in strengths:
                st.markdown(f"<span class='metric-badge badge-high'>✓ {s}</span>", unsafe_allow_html=True)
        else:
            st.info("No high-confidence skills yet. Complete assessments to prove skills.")

    with col_gap:
        st.markdown("##### ⚠️ Priority Skill Gaps (Need Practice)")
        gaps = data.get("top_gaps", [])
        if gaps:
            for g in gaps:
                st.markdown(f"<span class='metric-badge badge-low'>! {g}</span>", unsafe_allow_html=True)
        else:
            st.success("No critical skill gaps identified!")

    st.markdown("---")

    # Interactive Skill Gap Matrix Table
    st.markdown("##### 📋 Skill Matrix & Confidence Breakdown")
    matrix = data.get("skill_matrix", [])
    if matrix:
        table_rows = []
        for item in matrix:
            conf = item.get("confidence", "Low")
            conf_class = "badge-high" if conf == "High" else ("badge-medium" if conf == "Medium" else "badge-low")

            claimed_icon = "✓" if item.get("claimed") else "—"
            github_icon = "✓" if item.get("github_evidence") else "—"
            score_str = f"{item.get('assessment_score')}%" if item.get("assessment_score") is not None else "Unassessed"

            row_html = f"""
            <tr>
                <td><strong>{item.get('skill_name')}</strong></td>
                <td>{item.get('category')}</td>
                <td style="text-align: center;">{claimed_icon}</td>
                <td style="text-align: center;">{github_icon}</td>
                <td><strong>{score_str}</strong></td>
                <td><span class="metric-badge {conf_class}">{conf}</span></td>
                <td>{item.get('status')}</td>
            </tr>
            """
            table_rows.append(row_html)

        html_table = f"""
        <table class="styled-table">
            <thead>
                <tr>
                    <th>Skill</th>
                    <th>Category</th>
                    <th style="text-align: center;">Resume Claim</th>
                    <th style="text-align: center;">GitHub Proof</th>
                    <th>Assessment</th>
                    <th>Confidence</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
        """
        components.html(TABLE_CSS + html_table, height=max(200, 50 * len(matrix) + 60), scrolling=True)
    else:
        st.info("Upload your resume or add a target job description to build your personalized skill matrix.")
