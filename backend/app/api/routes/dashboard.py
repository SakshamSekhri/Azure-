from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.profile import StudentProfile
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.models.evidence import Evidence
from backend.app.models.learning_plan import LearningPlan
from backend.app.models.learning_activity import LearningActivity
from backend.app.schemas.dashboard import DashboardSummaryResponse
from backend.app.services.skill_service import SkillService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    student_name = profile.name if profile else "Student"
    target_role = profile.target_role if profile else "Full Stack Developer"
    github_connected = bool(profile and profile.github_username)

    resume_count = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    jd_count = db.query(JobDescription).filter(JobDescription.user_id == current_user.id).count()
    evidence_count = db.query(Evidence).filter(Evidence.user_id == current_user.id).count()

    matrix = SkillService.get_skill_matrix(db, current_user.id)
    recommended_action = SkillService.get_recommended_next_action(db, current_user.id)

    total_skills = len(matrix)
    assessed_skills = sum(1 for m in matrix if m.assessment_score is not None)
    strong_skills = [m.skill_name for m in matrix if m.confidence == "High"]
    weak_skills = [m.skill_name for m in matrix if m.confidence == "Low"]

    # Active learning plan progress
    active_plan = (
        db.query(LearningPlan)
        .filter(LearningPlan.user_id == current_user.id, LearningPlan.status == "active")
        .order_by(LearningPlan.generated_at.desc())
        .first()
    )
    plan_progress_pct = 0.0
    if active_plan:
        acts = db.query(LearningActivity).filter(LearningActivity.plan_id == active_plan.id).all()
        if acts:
            done = sum(1 for a in acts if a.completed)
            plan_progress_pct = round((done / len(acts)) * 100.0, 1)

    # Calculate overall preparation score deterministically
    if total_skills > 0:
        skill_score_sum = 0
        for m in matrix:
            if m.confidence == "High":
                skill_score_sum += 100
            elif m.confidence == "Medium":
                skill_score_sum += 65
            else:
                skill_score_sum += 30
        avg_skill_score = skill_score_sum / total_skills
        
        # Weighted preparation formula:
        # 60% skills confidence, 20% plan completion, 20% evidence completeness
        evidence_factor = min(100.0, (evidence_count / 5.0) * 100.0)
        overall_score = (avg_skill_score * 0.6) + (plan_progress_pct * 0.2) + (evidence_factor * 0.2)
    else:
        overall_score = 15.0 if (resume_count > 0 or jd_count > 0) else 5.0

    return DashboardSummaryResponse(
        student_name=student_name,
        target_role=target_role,
        overall_preparation_score=round(overall_score, 1),
        total_skills_tracked=total_skills,
        assessed_skills_count=assessed_skills,
        strong_skills_count=len(strong_skills),
        weak_skills_count=len(weak_skills),
        evidence_count=evidence_count,
        github_connected=github_connected,
        resume_uploaded=resume_count > 0,
        jd_uploaded=jd_count > 0,
        active_plan_progress_percentage=plan_progress_pct,
        top_strengths=strong_skills[:4],
        top_gaps=weak_skills[:4],
        recommended_action=recommended_action,
        skill_matrix=matrix,
        has_active_plan=active_plan is not None,
        plan_id=active_plan.id if active_plan else None
    )
