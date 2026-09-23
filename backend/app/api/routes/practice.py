from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.assessment import AssessmentResponse
from backend.app.schemas.practice import (
    PracticeGenerateRequest,
    FocusedAssessmentGenerateRequest,
    SkillFocusDetailResponse,
    TopicPerformanceItem
)
from backend.app.services.assessment_service import AssessmentService
from backend.app.services.skill_topic_service import SkillTopicService
from backend.app.services.skill_canonicalizer import canonicalize_skill

router = APIRouter()


@router.post("/generate", response_model=AssessmentResponse)
def generate_practice_session(
    req: PracticeGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate dynamic, adaptive 5-question practice session for ANY skill or topic strictly using Azure AI Foundry.
    Zero static questions, zero fallbacks. Adaptive difficulty based on skill/topic history.
    """
    return AssessmentService.generate_practice_session(
        db=db,
        user_id=current_user.id,
        skill=req.skill,
        topic=req.topic,
        num_questions=req.num_questions,
        difficulty=req.difficulty
    )


@router.post("/focused-assessment/generate", response_model=AssessmentResponse)
def generate_focused_assessment(
    req: FocusedAssessmentGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate comprehensive focused assessment (10 questions) for ANY skill or topic strictly using Azure AI Foundry."""
    return AssessmentService.generate_focused_assessment(
        db=db,
        user_id=current_user.id,
        skill=req.skill,
        topic=req.topic,
        num_questions=req.num_questions,
        difficulty=req.difficulty
    )


@router.get("/skills/focus", response_model=SkillFocusDetailResponse)
@router.get("/skills/{skill_identifier:path}/focus", response_model=SkillFocusDetailResponse)
def get_skill_focus(
    skill_identifier: Optional[str] = None,
    skill: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve comprehensive focus details for any skill: JD importance, current score, dynamic topics, accuracy, and next action."""
    target_skill = skill or skill_identifier
    if not target_skill:
        raise HTTPException(status_code=400, detail="Skill identifier is required.")
    return SkillTopicService.get_skill_focus_detail(
        db=db,
        user_id=current_user.id,
        skill_identifier=target_skill
    )


@router.get("/skills/topics", response_model=List[TopicPerformanceItem])
@router.get("/skills/{skill_identifier:path}/topics", response_model=List[TopicPerformanceItem])
def get_skill_topics(
    skill_identifier: Optional[str] = None,
    skill: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dynamically discover all topics for a given skill with candidate accuracy and status."""
    target_skill = skill or skill_identifier
    if not target_skill:
        raise HTTPException(status_code=400, detail="Skill identifier is required.")
    canon = canonicalize_skill(target_skill)
    return SkillTopicService.get_skill_topics(
        db=db,
        user_id=current_user.id,
        canonical_skill_id=canon.canonical_id,
        display_name=canon.display_name
    )
