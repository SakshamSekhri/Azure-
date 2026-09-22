from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.skill import Skill
from backend.app.schemas.skill import (
    SkillMatrixItem, SkillGapResponse, RecommendedActionResponse, SkillResponse,
    CandidateJDComparisonResponse
)
from backend.app.services.skill_service import SkillService

router = APIRouter()


@router.get("/matrix", response_model=List[SkillMatrixItem])
def get_matrix(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve skill comparison matrix."""
    return SkillService.get_skill_matrix(db, current_user.id)


@router.get("/candidate-vs-jd", response_model=CandidateJDComparisonResponse)
def get_candidate_vs_jd(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Compare candidate verified evidence directly against target Job Description requirements."""
    return SkillService.compare_candidate_vs_jd(db, current_user.id)


@router.get("/gaps", response_model=SkillGapResponse)
def get_gaps(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve categorized skill gaps (strong, moderate, weak, critical)."""
    return SkillService.calculate_skill_gaps(db, current_user.id)


@router.get("/recommended-action", response_model=RecommendedActionResponse)
def get_recommended_action(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate the single best next action for the student."""
    return SkillService.get_recommended_next_action(db, current_user.id)


@router.get("/all", response_model=List[SkillResponse])
def get_all_skills(db: Session = Depends(get_db)):
    return db.query(Skill).order_by(Skill.category, Skill.name).all()
