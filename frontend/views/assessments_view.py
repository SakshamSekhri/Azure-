import streamlit as st
import uuid
from typing import Dict, Any, Optional
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


def render_assessment_result_panel(
    result_data: Dict[str, Any],
    can_retake: bool = False,
    assessment_id: Optional[int] = None,
    key_prefix: str = "main"
):
    """Rich, deterministic assessment result and question-by-question review panel.
    Works independently of AI analysis status (Requirements 4, 5, 8, 9).
    """
    asm_id = result_data.get("assessment_id") or assessment_id or "default"
    att_id = result_data.get("attempt_id") or "latest"
    attempt_num = result_data.get("attempt_number", 1)
    title = result_data.get("title") or f"{result_data.get('role', 'Target Role')} Assessment"
    role = result_data.get("role") or "Target Role"
    completed_at = str(result_data.get("completed_at", ""))[:16].replace("T", " ")
    score = result_data.get("score_percentage", 0.0)
    passed = result_data.get("passed", False)
    badge_var = "success" if passed else "danger"
    analysis_status = result_data.get("analysis_status", "completed")

    # 1. Header Card (Requirement 8)
    render_html(
        f"""
        <div class="saas-panel" style="padding: 1.5rem 1.8rem; margin-top: 0.5rem; margin-bottom: 1.25rem; border-left: 4px solid {'#10B981' if passed else '#EF4444'};">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.05em;">
                        ASSESSMENT ATTEMPT #{attempt_num} REVIEW
                    </div>
                    <h2 style="margin: 0.2rem 0; font-size: 1.35rem; font-weight: 700; color: var(--text-primary);">{title}</h2>
                    <div style="font-size: 0.82rem; color: var(--text-secondary);">
                        Role: <strong>{role}</strong> &nbsp;|&nbsp; Attempt: <strong>#{attempt_num}</strong> &nbsp;|&nbsp; Completed: <strong>{completed_at}</strong>
                    </div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.95rem; font-weight: 700; color: var(--text-primary);">{score}%</div>
                    {render_status_badge('Passed' if passed else 'Needs Review', badge_var)}
                </div>
            </div>
        </div>
        """
    )

    # 2. AI Diagnostic Status Banner (Requirements 2, 8, 9)
    if analysis_status == "pending":
        render_html(
            """
            <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 0.9rem 1.25rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-size: 0.88rem; font-weight: 600; color: #B45309;">
                        ⏳ AI diagnostic analysis is still being generated...
                    </div>
                    <div style="font-size: 0.8rem; color: #92400E; margin-top: 0.15rem;">
                        Your deterministic score and complete question review are available immediately below. Recommendations will update once ready.
                    </div>
                </div>
            </div>
            """
        )
        c_ref, _ = st.columns([1, 4])
        with c_ref:
            if st.button("🔄 Refresh Diagnostic Status", key=f"{key_prefix}_poll_status_{asm_id}_{att_id}", use_container_width=True):
                st.rerun()

    elif analysis_status == "failed":
        render_html(
            """
            <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 8px; padding: 0.9rem 1.25rem; margin-bottom: 1.25rem; display: flex; align-items: center; justify-content: space-between;">
                <div>
                    <div style="font-size: 0.88rem; font-weight: 600; color: #DC2626;">
                        ⚠️ AI diagnostic analysis could not be generated at this time.
                    </div>
                    <div style="font-size: 0.8rem; color: #991B1B; margin-top: 0.15rem;">
                        All deterministic scores, answers, and explanations are safely preserved.
                    </div>
                </div>
            </div>
            """
        )
        c_retry, _ = st.columns([1, 4])
        with c_retry:
            if st.button("🔁 Retry AI Diagnostic Analysis", key=f"{key_prefix}_retry_analysis_{asm_id}_{att_id}", use_container_width=True):
                try:
                    api.retry_assessment_analysis(asm_id, att_id)
                    st.success("Retrying diagnostic analysis in background...")
                    st.rerun()
                except Exception as e:
                    st.error(f"Retry request failed: {e}")

    # 3. Performance Summary Metrics (Requirement 8)
    render_section_header("Performance Summary")
    total_q = result_data.get("total_questions", 0)
    corr_q = result_data.get("correct_count", 0)
    incorr_q = max(0, total_q - corr_q)
    dem_level = result_data.get("new_demonstrated_level", "Intermediate")
    conf = result_data.get("new_confidence", "Medium")

    col_m1, col_m2, col_m3, col_m4, col_m5, col_m6 = st.columns(6)
    with col_m1:
        st.metric("Score", f"{score}%")
    with col_m2:
        st.metric("Correct", f"{corr_q}")
    with col_m3:
        st.metric("Incorrect", f"{incorr_q}")
    with col_m4:
        st.metric("Total Questions", f"{total_q}")
    with col_m5:
        st.metric("Demonstrated Level", dem_level)
    with col_m6:
        st.metric("Confidence", conf)

    # 4. Skill Performance Breakdown (Requirement 8)
    per_skill = result_data.get("per_skill_scores") or {}
    if per_skill:
        st.write("")
        render_section_header("Skill-Level Performance")
        skill_cols = st.columns(min(len(per_skill), 3))
        for idx, (sk_name, sk_score) in enumerate(per_skill.items()):
            col_target = skill_cols[idx % len(skill_cols)]
            with col_target:
                render_progress_bar(sk_score, label=sk_name, height=7)

    # 5. Strengths vs Skill Gaps (Requirement 8)
    st.write("")
    col_str, col_gap = st.columns(2)
    with col_str:
        render_section_header("Demonstrated Strengths")
        strengths = result_data.get("strengths", [])
        if strengths:
            for s in strengths:
                render_html(f"<div style='font-size: 0.85rem; color: #166534; margin-bottom: 0.35rem;'>✓ <strong>{s}</strong></div>")
        else:
            st.caption("No strong technical competencies demonstrated yet.")

    with col_gap:
        render_section_header("Identified Skill Gaps")
        gaps = result_data.get("skill_gaps", []) or result_data.get("weaknesses", [])
        if gaps:
            for g in gaps:
                render_html(f"<div style='font-size: 0.85rem; color: #991B1B; margin-bottom: 0.35rem;'>⚠️ <strong>{g}</strong></div>")
        else:
            st.caption("No critical skill gaps identified.")

    # 6. Topics to Improve & Actionable Recommendations (Requirement 8)
    topics = result_data.get("topics_to_improve", [])
    if topics:
        st.write("")
        render_section_header("Topics to Review & Improve")
        topic_badges = "".join([f"<span class='status-badge badge-neutral' style='margin-right: 0.4rem; margin-bottom: 0.4rem; display: inline-block;'>{t}</span>" for t in topics])
        render_html(f"<div style='margin-bottom: 0.5rem;'>{topic_badges}</div>")

    plan_items = result_data.get("improvement_plan", [])
    if plan_items:
        st.write("")
        render_section_header("Actionable Improvement Recommendations")
        for p in plan_items:
            render_html(f"<div style='font-size: 0.85rem; color: var(--text-primary); margin-bottom: 0.35rem;'>• {p}</div>")

    summary_fb = result_data.get("summary_feedback")
    if summary_fb:
        st.write("")
        render_html(
            f"""
            <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-top: 0.5rem; margin-bottom: 1rem;">
                <div style="font-size: 0.74rem; font-weight: 700; color: var(--accent); text-transform: uppercase; margin-bottom: 0.25rem;">Diagnostic Summary Feedback</div>
                <div style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5;">{summary_fb}</div>
            </div>
            """
        )

    # 7. Question-by-Question Detailed Review (Requirements 5 & 8)
    st.write("")
    render_section_header("Question-by-Question Review", "Exact questions, your submitted responses, and verified solutions from this attempt.")

    details = result_data.get("details", [])
    if not details:
        st.caption("No individual question breakdown available for this attempt.")
    else:
        for idx, qd in enumerate(details, start=1):
            is_corr = qd.get("is_correct", False)
            user_ans = qd.get("selected_answer") or "Unanswered"
            corr_ans = qd.get("correct_answer") or ""
            expl = qd.get("explanation") or ""
            q_skill = qd.get("skill") or "Core"
            q_topic = qd.get("topic") or "General"
            q_concept = qd.get("concept") or "Core Concept"
            why_rel = qd.get("why_the_question_is_relevant") or ""
            q_options = qd.get("options") or []

            border_color = "#10B981" if is_corr else "#EF4444"
            status_text = "✅ Correct" if is_corr else "❌ Incorrect"
            status_color = "#166534" if is_corr else "#991B1B"
            user_ans_color = "#166534" if is_corr else "#DC2626"

            render_html(
                f"""
                <div style="background: var(--surface); border: 1px solid var(--border); border-left: 4px solid {border_color}; border-radius: 8px; padding: 1.15rem 1.35rem; margin-bottom: 1.25rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap;">
                        <span style="font-size: 0.74rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase;">
                            QUESTION {idx:02d} OF {len(details):02d} &nbsp;•&nbsp; {q_skill} &nbsp;•&nbsp; {q_topic} ({q_concept})
                        </span>
                        <span style="font-size: 0.82rem; font-weight: 700; color: {status_color};">
                            {status_text}
                        </span>
                    </div>
                    <div style="font-size: 0.98rem; font-weight: 600; color: var(--text-primary); line-height: 1.45; margin-bottom: 0.85rem;">
                        {qd.get('question')}
                    </div>
                    <div style="background: rgba(0,0,0,0.02); border-radius: 6px; padding: 0.65rem 0.85rem; margin-bottom: 0.65rem; font-size: 0.85rem; line-height: 1.5;">
                        <div style="margin-bottom: 0.25rem;">
                            Your Answer: <strong style="color: {user_ans_color};">{user_ans}</strong>
                        </div>
                        <div>
                            Correct Answer: <strong style="color: #166534;">{corr_ans}</strong>
                        </div>
                    </div>
                    <div style="font-size: 0.83rem; color: var(--text-secondary); margin-bottom: 0.4rem; line-height: 1.45;">
                        <strong>Explanation:</strong> {expl}
                    </div>
                    {f'<div style="font-size: 0.78rem; color: var(--text-muted); font-style: italic;">Why Relevant: {why_rel}</div>' if why_rel else ''}
                </div>
                """
            )

    # 8. Action Buttons (Requirement 6 & 14)
    st.write("")
    btn_col1, btn_col2 = st.columns([1, 1])
    with btn_col1:
        if can_retake and assessment_id:
            if st.button("🔄 Retake This Assessment (Start New Attempt)", key=f"{key_prefix}_retake_btn_{asm_id}_{att_id}", type="secondary", use_container_width=True):
                st.session_state[f"retaking_{assessment_id}"] = True
                st.session_state.pop(f"active_attempt_id_{assessment_id}", None)
                st.rerun()
    with btn_col2:
        if st.button("Proceed to Personalized Improvement Plan →", key=f"{key_prefix}_proceed_pip_{asm_id}_{att_id}", type="primary", use_container_width=True):
            st.session_state["pending_nav"] = "Personalized Improvement Plan"
            st.rerun()


def render_assessments_view():
    render_page_header(
        title="Personalized Assessment",
        subtitle="Dynamic AI evaluation synthesized from your resume claims, target job requirements, and skill gaps."
    )

    profile = {}
    resume = None
    job = None
    try:
        profile = api.get_profile() or {}
    except Exception:
        profile = {}

    try:
        resume = api.get_latest_resume()
    except Exception:
        resume = None

    if not resume and profile.get("active_resume"):
        resume = profile.get("active_resume")

    try:
        job = api.get_latest_job()
    except Exception:
        job = None

    if not job and profile.get("active_job"):
        job = profile.get("active_job")

    has_resume = bool(resume and (resume.get("has_content") or resume.get("raw_text") or resume.get("id")))
    has_job = bool(job and (job.get("has_content") or job.get("raw_text") or job.get("id") or job.get("exists")))

    target_role = (job.get("title") if has_job and job.get("title") else None) or (profile.get("target_role") if profile and profile.get("target_role") else None) or "Target Role"
    target_company = job.get("company") if has_job and job else None
    role_company_str = f"{target_role}" + (f" @ {target_company}" if target_company else "")

    if has_job:
        render_html(
            f"""
            <div style="margin-bottom: 1.25rem;">
                <span class="badge-role" style="font-size: 0.82rem; padding: 0.3rem 0.75rem;">
                    🎯 Target: <strong>{role_company_str}</strong>
                </span>
            </div>
            """
        )

    tab_current, tab_gen, tab_hist = st.tabs([
        "📝 Take Assessment",
        "✨ Generate New Assessment",
        "📜 Assessment History"
    ])

    # -------------------------------------------------------------
    # TAB 1: CURRENT ASSESSMENT (EXAM RUNNER OR COMPLETED RESULTS)
    # -------------------------------------------------------------
    with tab_current:
        try:
            assessments = api.list_assessments()
        except Exception as e:
            render_empty_state("Error Loading Assessments", str(e), icon="⚠️")
            return

        if not assessments:
            render_html(
                f"""
                <div class="saas-panel" style="padding: 1.5rem 1.8rem; border-left: 4px solid var(--accent);">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.25rem;">
                        PERSONALIZED ASSESSMENT READY TO GENERATE
                    </div>
                    <div style="font-size: 1.3rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.5rem;">
                        {target_role} Assessment
                    </div>
                    <div style="font-size: 0.84rem; color: var(--text-secondary); margin-bottom: 0.75rem;">
                        Synthesized dynamically by Azure AI Foundry specifically for your candidate background and target job requirements.
                    </div>
                    <div style="display: flex; gap: 1.5rem; font-size: 0.82rem; color: var(--text-muted); margin-bottom: 1rem;">
                        <span>📋 <strong>Dynamic Questions</strong></span>
                        <span>⏱️ <strong>Fast Submission</strong></span>
                        <span>🎯 <strong>Zero Hardcoded Questions</strong></span>
                    </div>
                </div>
                """
            )
            st.info("Switch to the **✨ Generate New Assessment** tab to launch your evaluation.")
        else:
            assessment_titles = {
                a["id"]: f"{a['title']} ({a.get('role') or 'Role'} • {a.get('status', 'pending').upper()})"
                for a in assessments
            }

            default_idx = 0
            if "active_assessment_id" in st.session_state and st.session_state["active_assessment_id"] in assessment_titles:
                default_idx = list(assessment_titles.keys()).index(st.session_state["active_assessment_id"])

            selected_id = st.selectbox(
                "Select Assessment Session",
                options=list(assessment_titles.keys()),
                index=default_idx,
                format_func=lambda x: assessment_titles[x]
            )

            assessment = next((a for a in assessments if a["id"] == selected_id), None)
            if assessment:
                status = assessment.get("status", "pending")
                is_retaking = st.session_state.get(f"retaking_{selected_id}", False)

                # State A: In Progress / Pending Exam or explicit retake mode
                if status != "completed" or is_retaking:
                    questions = assessment.get("questions", [])
                    render_html(
                        f"""
                        <div style="margin-top: 0.5rem; margin-bottom: 1rem;">
                            <div style="font-size: 0.75rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em;">
                                {'RETAKE EXAMINATION' if is_retaking else 'ACTIVE EXAMINATION'}
                            </div>
                            <h2 style="margin: 0.15rem 0; font-size: 1.25rem; font-weight: 700; color: var(--text-primary);">{assessment.get('title')}</h2>
                            <div style="font-size: 0.82rem; color: var(--text-secondary);">
                                Role: <strong>{assessment.get('role')}</strong> &nbsp;|&nbsp; Total Questions: <strong>{len(questions)}</strong>
                            </div>
                        </div>
                        """
                    )

                    answers = {}
                    # Initialize idempotency key for this exam session
                    if f"idemp_{selected_id}" not in st.session_state:
                        st.session_state[f"idemp_{selected_id}"] = str(uuid.uuid4())

                    attempt_form_key = f"exam_form_{selected_id}_{'retake' if is_retaking else 'initial'}"
                    with st.form(attempt_form_key):
                        for idx, q in enumerate(questions, start=1):
                            q_id = str(q["id"])
                            render_html(
                                f"""
                                <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1rem;">
                                    <div style="font-size: 0.74rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.35rem;">
                                        QUESTION {idx:02d} OF {len(questions):02d} &nbsp;•&nbsp; {q.get('skill', 'Core')}
                                    </div>
                                    <div style="font-size: 0.96rem; font-weight: 600; color: var(--text-primary); line-height: 1.45; margin-bottom: 0.75rem;">
                                        {q.get('question')}
                                    </div>
                                </div>
                                """
                            )

                            choice = st.radio(
                                f"Options for Q{idx}",
                                options=q.get("options", []),
                                key=f"asm_q_{q_id}_{'rt' if is_retaking else 'init'}",
                                index=None,
                                label_visibility="collapsed"
                            )
                            if choice:
                                answers[q_id] = choice
                            st.write("")

                        submitted = st.form_submit_button(
                            "Submit Assessment",
                            type="primary",
                            use_container_width=True
                        )

                    if submitted:
                        if len(answers) < len(questions):
                            st.warning(f"Please answer all questions before submitting. Answered {len(answers)} of {len(questions)}.")
                        else:
                            # Fast deterministic submission (Requirement 1, 10, 11)
                            with st.spinner("Submitting assessment..."):
                                try:
                                    res = api.submit_assessment(
                                        selected_id,
                                        answers,
                                        idempotency_key=st.session_state.get(f"idemp_{selected_id}")
                                    )
                                    # Reset idempotency key for future attempts
                                    st.session_state[f"idemp_{selected_id}"] = str(uuid.uuid4())
                                    st.session_state["active_assessment_id"] = selected_id
                                    st.session_state[f"active_attempt_id_{selected_id}"] = res.get("attempt_id")
                                    st.session_state[f"retaking_{selected_id}"] = False
                                    st.success("Assessment submitted successfully!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Submission failed: {str(e)}")

                # State B: Completed Exam Diagnostic Results (Requirement 1, 4, 8)
                else:
                    active_att_id = st.session_state.get(f"active_attempt_id_{selected_id}")
                    result_data = None
                    try:
                        if active_att_id:
                            result_data = api.get_assessment_attempt_result(selected_id, active_att_id)
                        if not result_data:
                            result_data = api.get_assessment_result(selected_id)
                    except Exception as e:
                        st.error(f"Failed to fetch results: {str(e)}")
                        return

                    if result_data:
                        render_assessment_result_panel(result_data, can_retake=True, assessment_id=selected_id, key_prefix="active")

    # -------------------------------------------------------------
    # TAB 2: GENERATE NEW ASSESSMENT
    # -------------------------------------------------------------
    with tab_gen:
        render_section_header("Configure New Personalized Assessment")
        
        c_r, c_j = st.columns(2)
        with c_r:
            st.markdown(f"**Resume Status**: {'✅ Active' if has_resume else '⚠️ Not Uploaded'}")
        with c_j:
            st.markdown(f"**Target Job Status**: {'✅ Linked' if has_job else '⚠️ Not Linked'}")

        if has_job and job:
            job_title = job.get("title") or target_role
            job_company = job.get("company") or ""
            company_display = f" @ {job_company}" if job_company else ""

            render_html(
                f"""
                <div class="saas-panel" style="padding: 1.15rem 1.4rem; margin: 1rem 0; border-left: 4px solid var(--accent); background: var(--surface);">
                    <div style="font-size: 0.72rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem;">
                        ACTIVE TARGET JOB (SINGLE SOURCE OF TRUTH)
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.3rem;">
                        🎯 Preparing for: {job_title}{company_display}
                    </div>
                    <div style="font-size: 0.82rem; color: var(--text-secondary);">
                        Target Evaluation Role: <strong style="color: var(--text-primary);">{job_title}</strong> (Derived automatically from your active target job)
                    </div>
                </div>
                """
            )

            q_count = st.select_slider("Number of Questions", options=[5, 10, 15], value=5)

            can_gen = has_resume and has_job
            if not has_resume:
                st.warning("Please upload your resume to generate a tailored evaluation.")

            if st.button("🚀 Generate Assessment via Azure AI Foundry", key="btn_generate_assessment_ai", type="primary", use_container_width=True, disabled=not can_gen):
                with st.spinner(f"Azure AI Foundry synthesizing {q_count} personalized MCQs for {job_title}..."):
                    try:
                        new_asm = api.generate_personalized_assessment(
                            role=job_title,
                            job_id=job.get("id"),
                            num_questions=q_count
                        )
                        st.success(f"Assessment '{new_asm.get('title')}' successfully generated!")
                        st.session_state["active_assessment_id"] = new_asm.get("id")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generation error: {str(e)}")
        else:
            render_empty_state(
                "Target Job Required",
                "Personalized assessments are dynamically synthesized strictly for your active target role. Please upload or link a Target Job to begin.",
                icon="🎯"
            )
            st.write("")
            if st.button("🎯 Go to Target Job", key="btn_goto_target_job_from_asm", type="primary"):
                st.session_state["nav_selection"] = "Target Job"
                st.rerun()

    # -------------------------------------------------------------
    # TAB 3: ASSESSMENT HISTORY & HISTORICAL REVIEW
    # -------------------------------------------------------------
    with tab_hist:
        # Check if an attempt is selected for deep historical review (Requirements 4, 5, 6, 8)
        review_attempt_id = st.session_state.get("view_history_attempt_id")
        review_assessment_id = st.session_state.get("view_history_assessment_id")

        if review_attempt_id and review_assessment_id:
            c_back, _ = st.columns([1, 4])
            with c_back:
                if st.button("← Back to History List", key="back_to_history_btn", use_container_width=True):
                    st.session_state.pop("view_history_attempt_id", None)
                    st.session_state.pop("view_history_assessment_id", None)
                    st.rerun()

            try:
                historical_attempt_data = api.get_assessment_attempt_result(review_assessment_id, review_attempt_id)
            except Exception as e:
                st.error(f"Error loading historical attempt review: {e}")
                return

            if historical_attempt_data:
                render_assessment_result_panel(historical_attempt_data, can_retake=False, assessment_id=review_assessment_id, key_prefix="history")
            else:
                render_empty_state("Attempt Not Found", "Unable to retrieve the requested assessment attempt result.", icon="⚠️")

        else:
            render_section_header("Past Assessment History", "Review all previous attempts, performance scores, and detailed question breakdowns.")
            try:
                history = api.get_assessment_history()
            except Exception:
                history = []

            if not history:
                render_empty_state("No History Yet", "Complete an assessment to view past evaluation scores and question reviews.", icon="📜")
            else:
                # Render clean attempt list with View Review button per attempt (Requirements 4 & 6)
                render_html(
                    """
                    <div style="display: grid; grid-template-columns: 2.5fr 1.5fr 1fr 1.2fr 1fr 1fr 1.2fr; padding: 0.6rem 0.75rem; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; font-size: 0.74rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.5rem;">
                        <div>Assessment</div>
                        <div>Role</div>
                        <div>Attempt</div>
                        <div>Date</div>
                        <div>Score</div>
                        <div>Result</div>
                        <div>Action</div>
                    </div>
                    """
                )

                for h in history:
                    att_id = h.get("attempt_id")
                    asm_id = h.get("assessment_id")
                    att_num = h.get("attempt_number", 1)
                    title = h.get("title") or f"{h.get('role', 'Target Role')} Assessment"
                    role = h.get("role", "Target Role")
                    dt_str = str(h.get("completed_at", ""))[:16].replace("T", " ")
                    score_val = h.get("score_percentage", 0.0)
                    passed = h.get("passed", False)
                    status_badge_html = render_status_badge("Passed", "success") if passed else render_status_badge("Review", "danger")

                    c_info, c_action = st.columns([5.8, 1.2])
                    with c_info:
                        render_html(
                            f"""
                            <div style="display: grid; grid-template-columns: 2.5fr 1.5fr 1fr 1.2fr 1fr 1fr; padding: 0.75rem 0.75rem; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; align-items: center; font-size: 0.84rem; margin-bottom: 0.35rem;">
                                <div><strong>{title}</strong></div>
                                <div style="color: var(--text-secondary);">{role}</div>
                                <div><span class="status-badge badge-neutral">Attempt #{att_num}</span></div>
                                <div style="color: var(--text-secondary); font-size: 0.8rem;">{dt_str}</div>
                                <div><strong>{score_val}%</strong></div>
                                <div>{status_badge_html}</div>
                            </div>
                            """
                        )
                    with c_action:
                        if st.button("View Review", key=f"btn_review_attempt_{att_id}", use_container_width=True):
                            st.session_state["view_history_attempt_id"] = att_id
                            st.session_state["view_history_assessment_id"] = asm_id
                            st.rerun()
