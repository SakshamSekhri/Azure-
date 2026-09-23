from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.learning import (
    LearningPlanGenerateRequest, LearningPlanDetailResponse,
    LearningActivityResponse, LearningActivityToggleRequest,
    RAGQueryRequest, GroundedRAGResponse, PersonalizedImprovementPlanResponse
)
from backend.app.services.learning_service import LearningService

router = APIRouter()


@router.get("/plan", response_model=Optional[LearningPlanDetailResponse])
def get_current_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve active 7-day personalized learning plan."""
    return LearningService.get_current_plan(db, current_user.id)


@router.get("/improvement-plan", response_model=PersonalizedImprovementPlanResponse)
def get_dynamic_improvement_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve dynamically prioritized improvement plan based on real-time readiness and gap analysis."""
    return LearningService.get_dynamic_improvement_plan(db, current_user.id)


@router.get("/plan/{plan_id}", response_model=LearningPlanDetailResponse)
def get_plan_by_id(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a specific learning plan, strictly verifying candidate ownership (Requirement 12)."""
    return LearningService.get_plan_by_id(db, current_user.id, plan_id)


@router.post("/plan/generate", response_model=LearningPlanDetailResponse)
def generate_plan(
    req: LearningPlanGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generates 7-day plan using structured AI call based on deterministic gaps."""
    return LearningService.generate_7day_plan(
        db=db,
        user_id=current_user.id,
        target_role=req.target_role,
        force_refresh=req.force_refresh
    )


@router.post("/activity/toggle", response_model=LearningActivityResponse)
def toggle_activity(
    req: LearningActivityToggleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a learning activity as completed or incomplete."""
    return LearningService.toggle_activity(
        db=db,
        user_id=current_user.id,
        activity_id=req.activity_id,
        completed=req.completed
    )


@router.post("/ask", response_model=GroundedRAGResponse)
def ask_question(
    req: RAGQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ask an educational question. System retrieves context from Azure AI Search / Knowledge Base, then answers."""
    return LearningService.ask_grounded_question(
        db=db,
        user_id=current_user.id,
        question=req.question,
        topic=req.topic,
        skill=req.skill
    )
