from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone

from backend.app.models.learning_plan import LearningPlan
from backend.app.models.learning_activity import LearningActivity
from backend.app.models.profile import StudentProfile
from backend.app.schemas.ai import LearningPlanResponse, RAGAnswerResponse
from backend.app.schemas.learning import LearningPlanDetailResponse, GroundedRAGResponse
from backend.app.services.skill_service import SkillService
from backend.app.ai.ai_gateway import AIGateway
from backend.app.rag.retrieval import retrieve_grounded_context
from backend.app.core.logging import logger


class LearningService:
    @staticmethod
    def get_current_plan(db: Session, user_id: int) -> Optional[LearningPlanDetailResponse]:
        plan = (
            db.query(LearningPlan)
            .filter(LearningPlan.user_id == user_id, LearningPlan.status == "active")
            .order_by(LearningPlan.generated_at.desc())
            .first()
        )
        if not plan:
            return None

        activities = (
            db.query(LearningActivity)
            .filter(LearningActivity.plan_id == plan.id)
            .order_by(LearningActivity.day_number.asc())
            .all()
        )

        completed_count = sum(1 for a in activities if a.completed)
        pct = (completed_count / len(activities) * 100.0) if activities else 0.0

        return LearningPlanDetailResponse(
            id=plan.id,
            user_id=plan.user_id,
            target_role=plan.target_role,
            duration_days=plan.duration_days,
            status=plan.status,
            summary=plan.summary,
            generated_at=plan.generated_at,
            activities=activities,
            completion_percentage=round(pct, 1)
        )

    @staticmethod
    def get_plan_by_id(db: Session, user_id: int, plan_id: int) -> LearningPlanDetailResponse:
        """Retrieve a specific learning plan strictly verifying candidate ownership (Requirement 12)."""
        plan = (
            db.query(LearningPlan)
            .filter(LearningPlan.id == plan_id, LearningPlan.user_id == user_id)
            .first()
        )
        if not plan:
            raise HTTPException(status_code=404, detail="Learning plan not found.")

        activities = (
            db.query(LearningActivity)
            .filter(LearningActivity.plan_id == plan.id)
            .order_by(LearningActivity.day_number.asc())
            .all()
        )

        completed_count = sum(1 for a in activities if a.completed)
        pct = (completed_count / len(activities) * 100.0) if activities else 0.0

        return LearningPlanDetailResponse(
            id=plan.id,
            user_id=plan.user_id,
            target_role=plan.target_role,
            duration_days=plan.duration_days,
            status=plan.status,
            summary=plan.summary,
            generated_at=plan.generated_at,
            activities=activities,
            completion_percentage=round(pct, 1)
        )

    @staticmethod
    def generate_7day_plan(
        db: Session,
        user_id: int,
        target_role: Optional[str] = None,
        force_refresh: bool = False
    ) -> LearningPlanDetailResponse:
        # Check active plan
        if not force_refresh:
            existing = LearningService.get_current_plan(db, user_id)
            if existing:
                logger.info(f"User {user_id} already has an active learning plan. Returning existing plan.")
                return existing

        # Deterministically extract gaps and strengths from PlacementProfile (Requirement 3 & 20)
        from backend.app.services.placement_profile_service import PlacementProfileService
        profile_data = PlacementProfileService.get_placement_profile(db, user_id)
        role = target_role or profile_data.candidate.target_role

        weak_skills_list = [g.display_name for g in profile_data.skill_gaps]
        if not weak_skills_list:
            gap_data = SkillService.calculate_skill_gaps(db, user_id)
            weak_skills_list = gap_data.weak_skills + gap_data.critical_gaps

        strong_skills_list = [v.display_name for v in profile_data.verified_skills]
        if not strong_skills_list:
            strong_skills_list = [s.display_name for s in profile_data.claimed_skills]

        payload = {
            "target_role": role,
            "weak_skills": weak_skills_list,
            "strong_skills": strong_skills_list,
            "weak_topics": profile_data.weak_topics,
            "per_skill_scores": profile_data.skill_scores
        }

        # Call AI Gateway for one-shot generation
        plan_response: LearningPlanResponse = AIGateway.execute(
            db=db,
            user_id=user_id,
            operation_type="LEARNING_PLAN",
            payload=payload,
            response_model=LearningPlanResponse,
            force_refresh=force_refresh
        )

        # Archive prior active plans
        db.query(LearningPlan).filter(
            LearningPlan.user_id == user_id,
            LearningPlan.status == "active"
        ).update({"status": "archived"})

        # Persist new LearningPlan
        db_plan = LearningPlan(
            user_id=user_id,
            target_role=role,
            duration_days=7,
            status="active",
            summary=plan_response.overview,
            generated_at=datetime.now(timezone.utc)
        )
        db.add(db_plan)
        db.commit()
        db.refresh(db_plan)

        # Persist activities
        db_activities = []
        for day_act in plan_response.days:
            act = LearningActivity(
                plan_id=db_plan.id,
                day_number=day_act.day,
                topic=day_act.topic,
                skill_name=day_act.skill,
                activity_type=day_act.activity_type,
                resource_url=day_act.resource_url,
                resource_description=f"{day_act.objective}\n\n{day_act.resource_description}",
                completed=False
            )
            db.add(act)
            db_activities.append(act)

        db.commit()
        for a in db_activities:
            db.refresh(a)

        return LearningPlanDetailResponse(
            id=db_plan.id,
            user_id=db_plan.user_id,
            target_role=db_plan.target_role,
            duration_days=7,
            status=db_plan.status,
            summary=db_plan.summary,
            generated_at=db_plan.generated_at,
            activities=db_activities,
            completion_percentage=0.0
        )

    @staticmethod
    def toggle_activity(db: Session, user_id: int, activity_id: int, completed: bool) -> LearningActivity:
        activity = (
            db.query(LearningActivity)
            .join(LearningPlan, LearningActivity.plan_id == LearningPlan.id)
            .filter(LearningActivity.id == activity_id, LearningPlan.user_id == user_id)
            .first()
        )
        if not activity:
            raise HTTPException(status_code=404, detail="Activity not found.")

        activity.completed = completed
        activity.completed_at = datetime.now(timezone.utc) if completed else None
        db.commit()
        db.refresh(activity)
        return activity

    @staticmethod
    def ask_grounded_question(
        db: Session,
        user_id: int,
        question: str,
        topic: Optional[str] = None,
        skill: Optional[str] = None
    ) -> GroundedRAGResponse:
        # 0. Determine Candidate Active Target Role
        from backend.app.services.job_service import JobService
        active_jd = JobService.get_active_target_job(db, user_id)
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        active_role = (
            (active_jd.title if active_jd and active_jd.title else None) or
            (profile.target_role if profile and profile.target_role else None) or
            "Placement Candidate"
        )

        # 1. Technical & Role Domain Guardrail Evaluation (Tier 3)
        from backend.app.rag.guardrails import check_domain_guardrail
        is_oob, oob_reason = check_domain_guardrail(query=question, active_role=active_role, topic=topic)
        if is_oob:
            logger.info(f"[GUARDRAIL TIER 3] Blocked out-of-bounds query '{question}' for role '{active_role}' (Reason: {oob_reason})")
            return GroundedRAGResponse(
                question=question,
                answer=(
                    f"This assistant is strictly dedicated to career placement preparation for {active_role}. "
                    f"I cannot provide answers for inquiries outside your target domain (such as {oob_reason}). "
                    f"Please ask a question related to {active_role} competencies, frameworks, or interview preparation."
                ),
                grounded=False,
                citations=[],
                confidence="None"
            )

        # 2. Retrieve bounded educational documents
        context_docs = retrieve_grounded_context(query=question, top_k=3, topic=topic)

        # 3. Package into payload
        payload = {
            "question": question,
            "target_role": active_role,
            "topic": topic,
            "skill": skill,
            "context_docs": context_docs
        }

        # 3. Call AI Gateway for grounded answer
        ai_result: RAGAnswerResponse = AIGateway.execute(
            db=db,
            user_id=user_id,
            operation_type="RAG_ANSWER",
            payload=payload,
            response_model=RAGAnswerResponse,
            force_refresh=False
        )

        return GroundedRAGResponse(
            question=ai_result.question,
            answer=ai_result.answer,
            grounded=ai_result.grounded,
            citations=ai_result.citations,
            confidence=ai_result.confidence
        )

    @staticmethod
    def get_dynamic_improvement_plan(db: Session, user_id: int):
        """Generates non-static, dynamic improvement plan automatically from candidate gaps,
        readiness analysis, and assessment/practice results. Automatically updates scores and
        progress as student practices.
        """
        from backend.app.models.job import JobDescription
        from backend.app.schemas.learning import (
            ImprovementPlanItem, PersonalizedImprovementPlanResponse, LearningActivityResponse
        )
        from backend.app.services.skill_canonicalizer import canonicalize_skill
        from backend.app.services.skill_topic_service import SkillTopicService

        # 1. Target role and company
        from backend.app.services.job_service import JobService
        latest_jd = JobService.get_active_target_job(db, user_id)
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()

        target_role = (latest_jd.title if latest_jd and latest_jd.title else None) or (profile.target_role if profile and profile.target_role else None) or "Candidate"
        target_company = latest_jd.company if latest_jd else None

        # 2. Extract JD requirements and candidate skill matrix
        matrix = SkillService.get_skill_matrix(db, user_id)
        comp = SkillService.compare_candidate_vs_jd(db, user_id)

        # Collect all distinct skills from JD requirements + matrix
        all_skill_names = set()
        if latest_jd and latest_jd.parsed_data:
            for r in latest_jd.parsed_data.get("required_skills", []):
                if r.get("name"):
                    all_skill_names.add(r["name"])
            for p in latest_jd.parsed_data.get("preferred_skills", []):
                if p.get("name"):
                    all_skill_names.add(p["name"])
        for m in matrix:
            all_skill_names.add(m.skill_name)

        if not all_skill_names:
            # Fallback only to candidate's own parsed resume skills (never hardcoded tech roles)
            from backend.app.models.resume import Resume
            latest_resume = db.query(Resume).filter(Resume.user_id == user_id).order_by(Resume.version.desc(), Resume.id.desc()).first()
            if latest_resume and latest_resume.parsed_data:
                for s in latest_resume.parsed_data.get("skills", []):
                    if isinstance(s, dict) and s.get("name"):
                        all_skill_names.add(s["name"])
                    elif isinstance(s, str) and s.strip():
                        all_skill_names.add(s.strip())

        # 3. For each skill, gather topic-level accuracy and build dynamic items
        active_items = []
        mastered_items = []

        req_names = {r.get("name", "").lower() for r in (latest_jd.parsed_data.get("required_skills", []) if latest_jd and latest_jd.parsed_data else [])}
        pref_names = {p.get("name", "").lower() for p in (latest_jd.parsed_data.get("preferred_skills", []) if latest_jd and latest_jd.parsed_data else [])}

        matrix_map = {m.skill_name.lower(): m for m in matrix}
        item_idx = 1

        for s_name in sorted(list(all_skill_names)):
            canon = canonicalize_skill(s_name)
            m_item = matrix_map.get(canon.canonical_id.lower()) or matrix_map.get(s_name.lower()) or matrix_map.get(canon.display_name.lower())

            skill_score = m_item.assessment_score if m_item else None
            is_required = (s_name.lower() in req_names or canon.canonical_id.lower() in req_names)
            is_preferred = (s_name.lower() in pref_names or canon.canonical_id.lower() in pref_names)

            # Discovered topics for this skill
            topics = SkillTopicService.get_skill_topics(db, user_id, canon.canonical_id, canon.display_name)

            for t in topics:
                acc = t.accuracy_percentage if t.accuracy_percentage is not None else (skill_score or 0.0)
                target = 80.0
                prog = round(min(100.0, (acc / target) * 100.0), 1)

                # Determine status (Not Started / In Progress / Mastered)
                if acc >= 80.0:
                    status = "Mastered"
                elif acc > 0.0 or (m_item and (m_item.claimed or m_item.assessment_score is not None)):
                    status = "In Progress"
                else:
                    status = "Not Started"

                # Determine priority & reason
                if is_required:
                    if acc < 50.0 or not m_item or not m_item.claimed:
                        prio = "HIGH"
                        reason = f"Required for target job {target_role} and weak in recent performance."
                    elif acc < 80.0:
                        prio = "HIGH"
                        reason = f"Required technical qualification. Current accuracy is {acc}%, needs {target}% for role readiness."
                    else:
                        prio = "MEDIUM"
                        reason = f"Required competency verified at {acc}% accuracy."
                elif is_preferred:
                    if acc < 60.0:
                        prio = "MEDIUM"
                        reason = f"Preferred qualification for {target_role} with room for technical improvement."
                    else:
                        prio = "LOW"
                        reason = f"Preferred competency demonstrated ({acc}% performance)."
                else:
                    if acc < 50.0:
                        prio = "HIGH"
                        reason = f"Identified weak skill area ({acc}% current score). Target is {target}% for proficiency."
                    elif acc < 80.0:
                        prio = "MEDIUM"
                        reason = f"Developing competency ({acc}% current score). Practice to reach {target}% benchmark."
                    else:
                        prio = "LOW"
                        reason = f"Supplementary tech stack item ({acc}% current score)."

                # Determine recommended action
                if status == "Mastered":
                    rec_action = "Assess"
                elif acc < 50.0 or t.weak_concepts or (not m_item or not m_item.claimed):
                    rec_action = "Learn"
                else:
                    rec_action = "Practice"

                item = ImprovementPlanItem(
                    id=f"imp_{canon.canonical_id}_{item_idx}",
                    skill=canon.display_name,
                    topic=t.topic,
                    current_score=round(acc, 1),
                    target_score=target,
                    priority=prio,
                    reason=reason,
                    status=status,
                    progress=prog,
                    recommended_action=rec_action
                )
                item_idx += 1

                if status == "Mastered":
                    mastered_items.append(item)
                else:
                    active_items.append(item)

        # Sort active items: HIGH first, then MEDIUM, then LOW
        prio_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}
        active_items.sort(key=lambda x: (prio_order.get(x.priority, 4), -x.progress))

        total = len(active_items) + len(mastered_items)
        total_prog = sum(i.progress for i in active_items) + (len(mastered_items) * 100.0)
        overall_pct = round(total_prog / max(total, 1), 1)

        # Fetch active 7-day plan activities if available
        active_plan = (
            db.query(LearningPlan)
            .filter(LearningPlan.user_id == user_id, LearningPlan.status == "active")
            .order_by(LearningPlan.generated_at.desc())
            .first()
        )
        plan_acts = []
        plan_summary = active_plan.summary if active_plan else None
        if active_plan:
            acts = (
                db.query(LearningActivity)
                .filter(LearningActivity.plan_id == active_plan.id)
                .order_by(LearningActivity.day_number.asc())
                .all()
            )
            plan_acts = [LearningActivityResponse.model_validate(a) for a in acts]

        return PersonalizedImprovementPlanResponse(
            target_role=target_role,
            target_company=target_company,
            active_items=active_items,
            mastered_items=mastered_items,
            total_items=total,
            overall_progress_percentage=overall_pct,
            active_plan_summary=plan_summary,
            activities=plan_acts
        )

