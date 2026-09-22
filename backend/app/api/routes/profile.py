from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.profile import StudentProfile
from backend.app.models.resume import Resume
from backend.app.models.job import JobDescription
from backend.app.schemas.profile import ProfileCreate, ProfileUpdate, ProfileResponse
from backend.app.schemas.resume import ResumeSummary
from backend.app.schemas.job import JobSummary
from backend.app.core.logging import logger

router = APIRouter()


def _build_profile_response(db: Session, user: User, profile: StudentProfile) -> ProfileResponse:
    """Build unified ProfileResponse with real-time database-backed active resume and job summaries."""
    active_resume = (
        db.query(Resume)
        .filter(Resume.user_id == user.id)
        .order_by(Resume.version.desc(), Resume.id.desc())
        .first()
    )
    active_job = (
        db.query(JobDescription)
        .filter(JobDescription.user_id == user.id)
        .order_by(JobDescription.id.desc())
        .first()
    )

    resume_summary = None
    if active_resume:
        resume_summary = ResumeSummary(
            id=active_resume.id,
            filename=active_resume.filename,
            version=active_resume.version,
            uploaded_at=active_resume.uploaded_at,
            has_content=bool(active_resume.raw_text and active_resume.raw_text.strip()),
            has_intelligence=bool(active_resume.parsed_data),
            file_hash=active_resume.file_hash
        )

    job_summary = None
    if active_job:
        job_summary = JobSummary(
            id=active_job.id,
            title=active_job.title,
            company=active_job.company,
            exists=True,
            has_content=bool(active_job.raw_text and active_job.raw_text.strip()),
            has_intelligence=bool(active_job.parsed_data),
            created_at=active_job.created_at
        )

    logger.info(
        f"[PROFILE SYNC] candidate_id={user.id} "
        f"active_resume_id={active_resume.id if active_resume else None} "
        f"active_resume_version={active_resume.version if active_resume else None} "
        f"resume_exists={bool(active_resume and active_resume.raw_text)} "
        f"resume_intelligence_exists={bool(active_resume and active_resume.parsed_data)} "
        f"job_id={active_job.id if active_job else None} "
        f"job_exists={bool(active_job and active_job.raw_text)}"
    )

    response = ProfileResponse.model_validate(profile)
    response.active_resume = resume_summary
    response.active_job = job_summary
    return response


@router.get("", response_model=ProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not profile:
        profile = StudentProfile(
            user_id=current_user.id,
            name=current_user.email.split("@")[0].capitalize(),
            target_role="Full Stack Developer",
            experience_level="Entry Level"
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return _build_profile_response(db, current_user, profile)


@router.put("", response_model=ProfileResponse)
def update_profile(
    profile_in: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).first()
    if not profile:
        profile = StudentProfile(user_id=current_user.id, name="Student")
        db.add(profile)

    update_data = profile_in.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        setattr(profile, field, val)

    db.commit()
    db.refresh(profile)
    return _build_profile_response(db, current_user, profile)
