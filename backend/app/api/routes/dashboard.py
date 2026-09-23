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
from backend.app.services.job_service import JobService

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    student_name = profile.name if profile else "Student"
    target_role = (profile.target_role if profile and profile.target_role else None) or "Target Role"
    github_connected = bool(profile and profile.github_username)

    resume_count = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    jd_count = db.query(JobDescription).filter(JobDescription.user_id == current_user.id).count()
    evidence_count = db.query(Evidence).filter(Evidence.user_id == current_user.id).count()

    matrix = SkillService.get_skill_matrix(db, current_user.id)
    recommended_action = SkillService.get_recommended_next_action(db, current_user.id)

    total_skills = len(matrix)
    assessed_scores = [m.assessment_score for m in matrix if m.assessment_score is not None]
    assessed_skills = len(assessed_scores)
    technical_knowledge = round(sum(assessed_scores) / max(assessed_skills, 1), 1) if assessed_skills > 0 else 0.0

    strong_skills = [m.skill_name for m in matrix if m.confidence == "High"]
    weak_skills = [m.skill_name for m in matrix if m.confidence == "Low"]

    # Candidate vs JD comparison
    comp = SkillService.compare_candidate_vs_jd(db, current_user.id)
    resume_match = comp.match_percentage
    jd_coverage = round((len(comp.evidence_found) + len(comp.needs_assessment)) / max(comp.total_jd_skills, 1) * 100.0, 1)

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

    # Calculate overall placement readiness score deterministically (Requirement 22)
    # 40% Technical Assessment Knowledge, 30% JD Skill Match, 20% Learning Plan Progress, 10% Evidence Completeness
    evidence_factor = min(100.0, (evidence_count / 5.0) * 100.0)
    if assessed_skills > 0:
        overall_score = (technical_knowledge * 0.40) + (resume_match * 0.30) + (plan_progress_pct * 0.20) + (evidence_factor * 0.10)
    elif resume_match > 0:
        overall_score = (resume_match * 0.50) + (plan_progress_pct * 0.30) + (evidence_factor * 0.20)
    else:
        overall_score = 15.0 if (resume_count > 0 or jd_count > 0) else 5.0

    # Active target job and company
    latest_jd = JobService.get_active_target_job(db, current_user.id)
    target_company = latest_jd.company if latest_jd else None
    if latest_jd and latest_jd.title:
        target_role = latest_jd.title

    # Assessment progress trajectory over time (Requirement 24)
    from backend.app.models.assessment_attempt import AssessmentAttempt
    from backend.app.models.assessment import Assessment

    attempts = (
        db.query(AssessmentAttempt)
        .filter(AssessmentAttempt.user_id == current_user.id)
        .order_by(AssessmentAttempt.completed_at.asc())
        .limit(10)
        .all()
    )
    progress_history = [
        {
            "attempt_number": att.attempt_number or idx,
            "score_percentage": att.score_percentage,
            "completed_at": att.completed_at.strftime("%Y-%m-%d %H:%M") if att.completed_at else None
        }
        for idx, att in enumerate(attempts, start=1)
    ]

    # Recent completed assessments (full or focused)
    recent_assessments_raw = (
        db.query(AssessmentAttempt, Assessment)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .filter(
            AssessmentAttempt.user_id == current_user.id,
            Assessment.assessment_mode.in_(["full_assessment", "focused_assessment"])
        )
        .order_by(AssessmentAttempt.completed_at.desc())
        .limit(5)
        .all()
    )
    recent_assessment_results = [
        {
            "attempt_id": att.id,
            "assessment_id": asm.id,
            "title": asm.title,
            "role": asm.role or asm.title,
            "score_percentage": att.score_percentage,
            "total_questions": att.total_questions,
            "correct_count": att.correct_count,
            "passed": att.score_percentage >= 60.0,
            "difficulty": asm.difficulty or "Intermediate",
            "completed_at": att.completed_at.strftime("%Y-%m-%d %H:%M") if att.completed_at else None
        }
        for att, asm in recent_assessments_raw
    ]

    # Recent practice sessions
    recent_practice_raw = (
        db.query(AssessmentAttempt, Assessment)
        .join(Assessment, AssessmentAttempt.assessment_id == Assessment.id)
        .filter(
            AssessmentAttempt.user_id == current_user.id,
            Assessment.assessment_mode == "practice"
        )
        .order_by(AssessmentAttempt.completed_at.desc())
        .limit(5)
        .all()
    )
    recent_practice_results = [
        {
            "attempt_id": att.id,
            "assessment_id": asm.id,
            "title": asm.title,
            "skill": asm.role or "General",
            "topic": asm.topic or "Core Concepts",
            "score_percentage": att.score_percentage,
            "total_questions": att.total_questions,
            "correct_count": att.correct_count,
            "passed": att.score_percentage >= 60.0,
            "difficulty": asm.difficulty or "Adaptive",
            "completed_at": att.completed_at.strftime("%Y-%m-%d %H:%M") if att.completed_at else None
        }
        for att, asm in recent_practice_raw
    ]

    return DashboardSummaryResponse(
        student_name=student_name,
        target_role=target_role,
        target_company=target_company,
        overall_preparation_score=round(overall_score, 1),
        resume_match_percentage=resume_match,
        jd_coverage_percentage=jd_coverage,
        technical_knowledge_percentage=technical_knowledge,
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
        progress_history=progress_history,
        recent_assessment_results=recent_assessment_results,
        recent_practice_results=recent_practice_results,
        has_active_plan=active_plan is not None,
        plan_id=active_plan.id if active_plan else None
    )
