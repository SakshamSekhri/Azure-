from typing import List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.assessment import (
    AssessmentResponse, AssessmentSubmission, AssessmentResultResponse,
    PersonalizedAssessmentRequest, AssessmentHistoryItem
)
from backend.app.services.assessment_service import AssessmentService

router = APIRouter()


@router.post("/personalized/generate", response_model=AssessmentResponse)
@router.post("/generate", response_model=AssessmentResponse)
def generate_personalized_assessment(
    req: PersonalizedAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate dynamic personalized assessment MCQs strictly using Azure AI Foundry.
    Zero predefined questions. Requires uploaded resume and job description.
    """
    return AssessmentService.generate_personalized_assessment(
        db=db,
        user_id=current_user.id,
        role=req.role,
        job_id=req.job_id,
        resume_text=req.resume,
        jd_text=req.job_description,
        num_questions=req.num_questions
    )


@router.get("", response_model=List[AssessmentResponse])
def list_assessments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List available personalized assessments for current candidate."""
    raw_list = AssessmentService.list_assessments(db, current_user.id)
    return [AssessmentService.get_assessment(db, a.id, user_id=current_user.id) for a in raw_list]


@router.get("/history", response_model=List[AssessmentHistoryItem])
def get_assessment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve full history of completed assessments with scores and diagnostic summaries."""
    return AssessmentService.get_assessment_history(db, current_user.id)


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Serve public assessment questions omitting correct answers and explanations with ownership verification."""
    return AssessmentService.get_assessment(db, assessment_id, user_id=current_user.id)


@router.post("/{assessment_id}/submit", response_model=AssessmentResultResponse)
def submit_assessment(
    assessment_id: int,
    submission: AssessmentSubmission,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deterministically score MCQ assessment, persist every answer, and run Azure AI diagnostic analysis asynchronously."""
    return AssessmentService.submit_assessment(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
        submitted_answers=submission.answers,
        duration_seconds=submission.duration_seconds,
        idempotency_key=submission.idempotency_key,
        background_tasks=background_tasks
    )


@router.get("/{assessment_id}/result", response_model=AssessmentResultResponse)
def get_assessment_result(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve stored results of the latest completed attempt for an assessment. Persists across page refresh."""
    return AssessmentService.get_assessment_result(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id
    )


@router.get("/{assessment_id}/attempts/{attempt_id}/result", response_model=AssessmentResultResponse)
def get_assessment_attempt_result(
    assessment_id: int,
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve stored results of a specific historical assessment attempt with ownership verification."""
    return AssessmentService.get_assessment_attempt_result(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
        attempt_id=attempt_id
    )


@router.post("/{assessment_id}/attempts/{attempt_id}/retry-analysis", response_model=AssessmentResultResponse)
def retry_assessment_analysis(
    assessment_id: int,
    attempt_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retry failed AI diagnostic analysis for an attempt asynchronously."""
    return AssessmentService.retry_assessment_analysis(
        db=db,
        user_id=current_user.id,
        assessment_id=assessment_id,
        attempt_id=attempt_id,
        background_tasks=background_tasks
    )
