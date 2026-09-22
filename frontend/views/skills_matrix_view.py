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


def render_skills_matrix_view():
    st.markdown("### 🧩 Skill Gaps & Readiness Analytics")
    st.markdown("Rigorous comparison of **Candidate Evidence** vs. **Job Requirements** vs. **Objective Assessment Scores**.")
    st.markdown("<span class='credit-pill'>⚡ Evidence Grounded — Zero Hallucination in Skill Possession</span>", unsafe_allow_html=True)

    # 1. Candidate vs JD Comparison Overview
    try:
        cand_jd = api.get_candidate_vs_jd()
    except Exception:
        cand_jd = None

    if cand_jd:
        st.markdown("---")
        st.markdown(f"#### 🎯 Candidate vs. Target Job Comparison ({cand_jd.get('target_role')})")
        
        m_pct = cand_jd.get("match_percentage", 0.0)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("JD Match Rate", f"{m_pct}%")
        c2.metric("Evidence Found", len(cand_jd.get("evidence_found", [])))
        c3.metric("Needs Assessment", len(cand_jd.get("needs_assessment", [])))
        c4.metric("Skill Gaps", len(cand_jd.get("skill_gaps", [])))

        col_ef, col_na, col_sg, col_un = st.columns(4)
        with col_ef:
            st.markdown("##### 🟢 Evidence Found")
            ef_list = cand_jd.get("evidence_found", [])
            if ef_list:
                for item in ef_list:
                    st.markdown(f"- ✅ **{item}**")
            else:
                st.caption("No verified skills yet.")

        with col_na:
            st.markdown("##### 🟡 Needs Assessment")
            na_list = cand_jd.get("needs_assessment", [])
            if na_list:
                for item in na_list:
                    st.markdown(f"- ⏳ **{item}**")
            else:
                st.caption("None pending.")

        with col_sg:
            st.markdown("##### 🔴 Skill Gaps")
            sg_list = cand_jd.get("skill_gaps", [])
            if sg_list:
                for item in sg_list:
                    st.markdown(f"- ⚠️ **{item}**")
            else:
                st.caption("No critical gaps!")

        with col_un:
            st.markdown("##### ⚪ Unknown")
            un_list = cand_jd.get("unknown", [])
            if un_list:
                for item in un_list:
                    st.markdown(f"- ❓ **{item}**")
            else:
                st.caption("No unknown skills.")

    st.markdown("---")

    # 2. Detailed Tracked Skill Matrix
    st.markdown("#### 📋 Tracked Competency Matrix")
    try:
        matrix = api.get_skill_matrix()
    except Exception as e:
        st.error(f"Error loading skill matrix: {str(e)}")
        return

    if not matrix:
        st.info("No skills tracked yet. Upload your resume or job description to initialize your skill matrix.")
        return

    # Category Filter
    categories = sorted(list(set(m.get("category", "General") for m in matrix)))
    selected_cat = st.selectbox("Filter by Category", ["All Categories"] + categories)

    filtered_matrix = matrix
    if selected_cat != "All Categories":
        filtered_matrix = [m for m in matrix if m.get("category") == selected_cat]

    # Render Styled Table
    table_rows = []
    for item in filtered_matrix:
        conf = item.get("confidence", "Low")
        conf_class = "badge-high" if conf == "High" else ("badge-medium" if conf == "Medium" else "badge-low")

        claimed_icon = "✓ Claimed" if item.get("claimed") else "—"
        github_icon = "✓ Supporting" if item.get("github_evidence") else "—"
        score = item.get("assessment_score")
        score_display = f"<strong>{score}%</strong>" if score is not None else "<span style='color: #94a3b8;'>Unassessed</span>"

        row_html = f"""
        <tr>
            <td><strong>{item.get('skill_name')}</strong></td>
            <td><span class="metric-badge badge-info">{item.get('category')}</span></td>
            <td style="text-align: center;">{claimed_icon}</td>
            <td style="text-align: center;">{github_icon}</td>
            <td>{score_display}</td>
            <td><span class="metric-badge {conf_class}">{conf}</span></td>
            <td>{item.get('status')}</td>
        </tr>
        """
        table_rows.append(row_html)

    html_table = f"""
    <table class="styled-table">
        <thead>
            <tr>
                <th>Skill Name</th>
                <th>Category</th>
                <th style="text-align: center;">Resume</th>
                <th style="text-align: center;">GitHub Evidence</th>
                <th>Objective Score</th>
                <th>Confidence Level</th>
                <th>Preparation Status</th>
            </tr>
        </thead>
        <tbody>
            {''.join(table_rows)}
        </tbody>
    </table>
    """
    components.html(TABLE_CSS + html_table, height=max(200, 50 * len(filtered_matrix) + 60), scrolling=True)

    st.markdown("---")
    st.markdown("##### 💡 Confidence Calibration Rules:")
    st.markdown("""
    - **High Confidence**: Assessment Score ≥ 75%, or ≥ 65% with verified GitHub code & resume claim.
    - **Medium Confidence**: Assessment Score 50% - 74%, or claimed in resume with supporting GitHub code.
    - **Low Confidence**: Assessment Score < 50%, or claimed without verification proof.
    - **Critical Gap**: Required by target job but unverified or failed assessment.
    """)
