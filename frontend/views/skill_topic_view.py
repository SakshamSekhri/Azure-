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


def render_skill_topic_view():
    # Check if currently inside an active practice exam session
    active_practice = st.session_state.get("active_practice_data")
    if active_practice:
        render_active_practice_runner(active_practice, st.session_state.get("focus_skill", "General"))
        return

    # Check if viewing results from a completed practice session
    practice_result = st.session_state.get("last_practice_result")
    if practice_result:
        render_practice_result_view(practice_result, st.session_state.get("focus_skill", "General"))
        return

    render_page_header(
        title="Skills & Topic Practice",
        subtitle="Interactive topic-by-topic learning platform. Practice targeted questions to raise competency scores."
    )

    # Contextual Target Job Badge
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

    # 1. Skill Selector (Derived from Active Target Job & Resume)
    available_skills = []

    # 1a. Skills from active target job requirements
    try:
        latest_job = api.get_latest_job()
        if latest_job and latest_job.get("parsed_data"):
            req_s = latest_job["parsed_data"].get("required_skills", [])
            pref_s = latest_job["parsed_data"].get("preferred_skills", [])
            for item in req_s + pref_s:
                name = item.get("name") if isinstance(item, dict) else str(item)
                if name and name not in available_skills:
                    available_skills.append(name)
    except Exception:
        pass

    # 1b. Skills from active resume
    try:
        latest_res = api.get_latest_resume()
        if latest_res and latest_res.get("parsed_data"):
            for item in latest_res["parsed_data"].get("skills", []):
                name = item.get("name") if isinstance(item, dict) else str(item)
                if name and name not in available_skills:
                    available_skills.append(name)
    except Exception:
        pass

    # 1c. Skills from skill matrix & candidate vs JD
    try:
        matrix = api.get_skill_matrix()
        for m in matrix:
            s_name = m.get("skill_name")
            if s_name and s_name not in available_skills:
                available_skills.append(s_name)
    except Exception:
        pass

    try:
        cand_jd = api.get_candidate_vs_jd()
        if cand_jd:
            for item in cand_jd.get("items", []):
                s_name = item.get("skill_name")
                if s_name and s_name not in available_skills:
                    available_skills.append(s_name)
    except Exception:
        pass

    selected_skill = None
    if available_skills:
        default_skill = st.session_state.get("focus_skill") or available_skills[0]
        if default_skill not in available_skills:
            available_skills.insert(0, default_skill)
        default_index = available_skills.index(default_skill) if default_skill in available_skills else 0

        col_sel, col_custom = st.columns([2.5, 1.5])
        with col_sel:
            selected_skill = st.selectbox(
                "Select Skill to Practice",
                available_skills,
                index=default_index,
                key="practice_skill_select"
            )
        with col_custom:
            custom_input = st.text_input("Or Type Any Skill / Technology", placeholder="e.g. Brand Strategy, Market Research")
            if custom_input and custom_input.strip():
                selected_skill = custom_input.strip()
    else:
        custom_input = st.text_input(
            "Enter Skill to Practice",
            value=st.session_state.get("focus_skill", ""),
            placeholder="e.g. Brand Strategy, Content Marketing, Market Research"
        )
        if custom_input and custom_input.strip():
            selected_skill = custom_input.strip()
        else:
            render_empty_state(
                "No Skills Detected Yet",
                "Link a Target Job or upload a Resume to populate skills for your role, or type a skill above to begin practicing.",
                icon="🎯"
            )
            return

    st.session_state["focus_skill"] = selected_skill

    # 2. Fetch Skill Focus Detail
    try:
        with st.spinner(f"Loading topic profile for {selected_skill}..."):
            focus_data = api.get_skill_focus(selected_skill)
    except Exception as e:
        render_empty_state("Skill Focus Error", f"Failed to load details for {selected_skill}: {str(e)}", icon="⚠️")
        return

    skill_name = focus_data.get("skill_name", selected_skill)
    category = focus_data.get("category", "General")
    importance = focus_data.get("jd_importance", "Bonus")
    score = focus_data.get("current_score")
    conf = focus_data.get("confidence", "None")
    demonstrated = focus_data.get("demonstrated_level", "Unassessed")
    score_num = round(score, 1) if score is not None else 0.0

    # 3. Clean Skill Header Strip (No oversized cards)
    render_html(
        f"""
        <div class="saas-panel" style="margin-top: 0.5rem; margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.8rem;">
                <div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <h2 style="margin: 0; font-size: 1.25rem; font-weight: 700; color: var(--text-primary);">{skill_name}</h2>
                        {render_status_badge(category, 'info')}
                        {render_status_badge(importance, 'warning' if importance == 'Required' else 'neutral')}
                    </div>
                    <div style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.25rem;">
                        Demonstrated Level: <strong>{demonstrated}</strong> (Confidence: {conf})
                    </div>
                </div>
                <div style="text-align: right; min-width: 140px;">
                    <div style="font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{f'{score_num}%' if score is not None else 'Unassessed'}</div>
                    <div class="saas-bar-track" style="width: 140px; height: 5px;">
                        <div class="saas-bar-fill" style="width: {min(100.0, score_num)}%; background-color: {'#10B981' if score_num >= 80 else ('#6366F1' if score_num >= 60 else '#EF4444')};"></div>
                    </div>
                </div>
            </div>
        </div>
        """
    )

    # -------------------------------------------------------------
    # 4. TOPIC BREAKDOWN (LEARNING PLATFORM FEEL)
    # -------------------------------------------------------------
    topics = focus_data.get("topic_breakdown", []) or focus_data.get("topics", [])
    render_section_header("Topic Mastery & Practice", "Select a specific topic to practice adaptive questions")

    if topics:
        for idx, t in enumerate(topics):
            t_name = t.get("topic", "General Topic")
            acc = t.get("accuracy_percentage")
            acc_num = round(acc, 1) if acc is not None else 0.0
            corr = t.get("correct_answers", 0)
            att = t.get("total_attempts", 0)
            status_lbl = t.get("mastery_status", "Unassessed")
            
            badge_var = "success" if acc_num >= 80.0 else ("warning" if acc_num >= 60.0 else ("danger" if att > 0 else "neutral"))

            render_html(
                f"""
                <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem 1.1rem; margin-bottom: 0.6rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                        <span style="font-weight: 600; font-size: 0.92rem; color: var(--text-primary);">{t_name}</span>
                        <div>
                            <span style="font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); margin-right: 0.4rem;">{f'{acc_num}% ({corr}/{att})' if att > 0 else 'Not attempted yet'}</span>
                            {render_status_badge(status_lbl, badge_var)}
                        </div>
                    </div>
                    <div class="saas-bar-track" style="height: 5px; margin-bottom: 0.5rem;">
                        <div class="saas-bar-fill" style="width: {min(100.0, acc_num)}%; background-color: {'#10B981' if acc_num >= 80 else ('#6366F1' if acc_num >= 60 else '#CBD5E1')};"></div>
                    </div>
                </div>
                """
            )

            col_p, col_l, _ = st.columns([1.2, 1.2, 3])
            with col_p:
                if st.button("🎯 Practice Topic", key=f"btn_prac_{idx}", use_container_width=True):
                    with st.spinner(f"Generating 5 adaptive questions for '{t_name}'..."):
                        try:
                            sess = api.generate_practice(skill=skill_name, topic=t_name, num_questions=5)
                            st.session_state["active_practice_data"] = sess
                            st.session_state["practice_topic"] = t_name
                            st.session_state["last_practice_result"] = None
                            st.rerun()
                        except Exception as err:
                            st.error(f"Practice generation failed: {str(err)}")
            with col_l:
                if st.button("📚 Learn Concept", key=f"btn_learn_{idx}", use_container_width=True):
                    st.session_state["rag_prefill_query"] = f"Explain {t_name} in {skill_name} with key patterns, practical implementation, and interview edge cases."
                    st.session_state["rag_prefill_topic"] = t_name
                    st.session_state["pending_nav"] = "RAG Assistant"
                    st.rerun()

            st.write("")
    else:
        st.caption("No fine-grained topic breakdown recorded yet. Use the launcher below to begin practicing.")

    st.markdown("---")

    # -------------------------------------------------------------
    # 5. CUSTOM PRACTICE LAUNCHER
    # -------------------------------------------------------------
    render_section_header("⚡ Custom Practice Session", "Configure a customized adaptive quiz")
    col_opt1, col_opt2, col_opt3 = st.columns(3)

    topic_options = ["All Topics / Core Concepts"] + [t.get("topic") for t in topics]
    with col_opt1:
        chosen_topic = st.selectbox("Focus Area / Topic", topic_options, key="launcher_topic")
    with col_opt2:
        q_count = st.selectbox("Number of Questions", [3, 5, 10], index=1, key="launcher_count")
    with col_opt3:
        difficulty_mode = st.selectbox("Difficulty Mode", ["Adaptive (Recommended)", "Beginner", "Intermediate", "Advanced"], index=0, key="launcher_diff")

    diff_param = None if "Adaptive" in difficulty_mode else difficulty_mode
    topic_param = None if chosen_topic == "All Topics / Core Concepts" else chosen_topic

    if st.button(f"🚀 Start Practice Session ({q_count} Questions)", type="primary", use_container_width=True):
        with st.spinner(f"Synthesizing {q_count} adaptive questions for {skill_name}..."):
            try:
                sess = api.generate_practice(
                    skill=skill_name,
                    topic=topic_param,
                    num_questions=q_count,
                    difficulty=diff_param
                )
                st.session_state["active_practice_data"] = sess
                st.session_state["practice_topic"] = topic_param or "Core Concepts"
                st.session_state["last_practice_result"] = None
                st.rerun()
            except Exception as err:
                st.error(f"Generation error: {str(err)}")


def render_active_practice_runner(practice_data, skill_name):
    """Distraction-free, clean practice test taker interface."""
    assessment_id = practice_data.get("id")
    title = practice_data.get("title", f"Practice: {skill_name}")
    diff = practice_data.get("difficulty", "Adaptive")
    topic = st.session_state.get("practice_topic") or practice_data.get("topic") or "General"
    questions = practice_data.get("questions", [])

    render_html(
        f"""
        <div style="margin-bottom: 1.5rem;">
            <div style="font-size: 0.72rem; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em;">ACTIVE PRACTICE SESSION</div>
            <h1 style="margin: 0.2rem 0; font-size: 1.5rem; font-weight: 700; color: var(--text-primary);">{title}</h1>
            <div style="font-size: 0.82rem; color: var(--text-secondary);">
                Skill: <strong>{skill_name}</strong> &nbsp;|&nbsp; Topic: <strong>{topic}</strong> &nbsp;|&nbsp; Difficulty: <strong>{diff}</strong>
            </div>
        </div>
        """
    )

    if not questions:
        render_empty_state("No Questions Available", "The practice session contains no questions. Please cancel and retry.")
        if st.button("Cancel Session"):
            st.session_state["active_practice_data"] = None
            st.rerun()
        return

    user_answers = {}
    with st.form("practice_exam_form"):
        for idx, q in enumerate(questions, start=1):
            q_id = str(q.get("id"))
            q_text = q.get("question")
            options = q.get("options", [])
            q_topic = q.get("topic", topic)

            render_html(
                f"""
                <div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1.1rem 1.25rem; margin-bottom: 1rem;">
                    <div style="font-size: 0.74rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.35rem;">QUESTION {idx:02d} OF {len(questions):02d} &nbsp;•&nbsp; {q_topic}</div>
                    <div style="font-size: 0.96rem; font-weight: 600; color: var(--text-primary); line-height: 1.45; margin-bottom: 0.75rem;">{q_text}</div>
                </div>
                """
            )

            selected = st.radio(
                f"Options for Question {idx}",
                options,
                key=f"q_radio_{q_id}",
                index=None,
                label_visibility="collapsed"
            )
            if selected:
                user_answers[q_id] = selected

            st.write("")

        submitted = st.form_submit_button("Submit Practice Answers", type="primary", use_container_width=True)

    c_cancel, _ = st.columns([1.5, 3])
    with c_cancel:
        if st.button("Cancel Practice Session", use_container_width=True):
            st.session_state["active_practice_data"] = None
            st.rerun()

    if submitted:
        if len(user_answers) < len(questions):
            st.warning(f"Please answer all questions before submitting. Answered {len(user_answers)} of {len(questions)}.")
            return

        with st.spinner("Scoring practice deterministically and updating competency profile..."):
            try:
                result = api.submit_assessment(assessment_id, user_answers)
                st.session_state["active_practice_data"] = None
                st.session_state["last_practice_result"] = result
                st.success("Practice submitted successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Submission failed: {str(e)}")


def render_practice_result_view(result, skill_name):
    """Clean post-practice results and diagnostic feedback."""
    score = result.get("score_percentage", 0.0)
    total_q = result.get("total_questions", 0)
    corr_q = result.get("correct_count", 0)
    topic = result.get("topic") or st.session_state.get("practice_topic") or "General"
    details = result.get("details", [])

    render_page_header(
        title="Practice Session Results",
        subtitle=f"Performance evaluation for {skill_name} ({topic})"
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("Final Score", f"{score}%")
    c2.metric("Accuracy", f"{corr_q} / {total_q} Correct")
    c3.metric("Topic Focus", topic)

    st.write("")
    if score >= 80.0:
        st.success(f"🎉 **Topic Mastery!** You scored {score}% in {topic}. This competency has advanced in your skill profile.")
    else:
        st.info(f"💡 Score: {score}%. Review the explanations below and practice again to reach the 80% benchmark.")

    # Question Review Cards
    render_section_header("Question Diagnostic Review")
    for idx, d in enumerate(details, start=1):
        is_corr = d.get("is_correct")
        icon = "✓" if is_corr else "✕"
        badge_variant = "success" if is_corr else "danger"
        q_concept = d.get("concept") or "Core Concept"

        render_html(
            f"""
            <div style="background: var(--surface); border: 1px solid var(--border); border-left: 4px solid {'#10B981' if is_corr else '#EF4444'}; border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 0.75rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                    <span style="font-weight: 600; font-size: 0.92rem; color: var(--text-primary);">{icon} Question {idx}: {d.get('question')}</span>
                    {render_status_badge('Correct' if is_corr else 'Incorrect', badge_variant)}
                </div>
                <div style="font-size: 0.84rem; color: var(--text-secondary); margin-top: 0.4rem;">
                    Your Answer: <strong style="color: {'#10B981' if is_corr else '#EF4444'};">{d.get('selected_answer')}</strong>
                </div>
                {f'<div style="font-size: 0.84rem; color: #10B981; margin-top: 0.2rem;">Correct Answer: <strong>{d.get("correct_answer")}</strong></div>' if not is_corr else ''}
                <div style="font-size: 0.82rem; color: var(--text-muted); margin-top: 0.45rem; line-height: 1.45;">
                    <em>{d.get('explanation', '')}</em>
                </div>
            </div>
            """
        )

        if not is_corr:
            if st.button(f"📚 Learn Concept '{q_concept}' in RAG Assistant", key=f"rag_q_{idx}"):
                st.session_state["rag_prefill_query"] = f"Explain the technical concept of '{q_concept}' in {skill_name} ({topic}). Why is '{d.get('correct_answer')}' the correct pattern?"
                st.session_state["rag_prefill_topic"] = topic
                st.session_state["pending_nav"] = "RAG Assistant"
                st.rerun()

    st.write("")
    c_btn1, c_btn2, _ = st.columns([1.5, 1.5, 2])
    with c_btn1:
        if st.button("Practice Another 5 Questions", type="primary", use_container_width=True):
            with st.spinner(f"Generating new practice session on {topic}..."):
                try:
                    sess = api.generate_practice(skill=skill_name, topic=topic, num_questions=5)
                    st.session_state["active_practice_data"] = sess
                    st.session_state["last_practice_result"] = None
                    st.rerun()
                except Exception as err:
                    st.error(f"Error: {err}")
    with c_btn2:
        if st.button("Return to Topic Explorer", use_container_width=True):
            st.session_state["last_practice_result"] = None
            st.rerun()
