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

        # Deterministically extract gaps and strengths
        gap_data = SkillService.calculate_skill_gaps(db, user_id)
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        role = target_role or (profile.target_role if profile else "Full Stack Developer")

        payload = {
            "target_role": role,
            "weak_skills": gap_data.weak_skills + gap_data.critical_gaps,
            "strong_skills": gap_data.strong_skills
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
        """One-shot grounded RAG answer."""
        # 1. Retrieve bounded educational documents
        context_docs = retrieve_grounded_context(query=question, top_k=3, topic=topic)

        # 2. Package into payload
        payload = {
            "question": question,
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
