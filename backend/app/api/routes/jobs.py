from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.job import JobDescription
from backend.app.schemas.job import (
    JobDescriptionCreate, JobDescriptionResponse, JobAnalysisRequest
)
from backend.app.services.job_service import JobService

router = APIRouter()


@router.post("", response_model=JobDescriptionResponse)
def create_job_description(
    job_in: JobDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Store raw job description. Does NOT call AI automatically."""
    job = JobService.create_job_description(
        db=db,
        user_id=current_user.id,
        title=job_in.title,
        raw_text=job_in.raw_text,
        company=job_in.company
    )
    return job


@router.post("/analyze", response_model=JobDescriptionResponse)
def analyze_job_description(
    request: JobAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Explicitly triggered by 'Analyze Job Description' button."""
    job = JobService.analyze_job_description(
        db=db,
        user_id=current_user.id,
        job_id=request.job_id,
        force_refresh=request.force_refresh
    )
    return job


@router.get("/latest", response_model=JobDescriptionResponse)
def get_latest_job(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.app.core.logging import logger
    job = (
        db.query(JobDescription)
        .filter(JobDescription.user_id == current_user.id)
        .order_by(JobDescription.created_at.desc(), JobDescription.id.desc())
        .first()
    )
    if not job:
        logger.info(f"[JOB GET_LATEST] candidate_id={current_user.id} job_found=False")
        raise HTTPException(status_code=404, detail="No job description on file.")

    logger.info(
        f"[JOB GET_LATEST] candidate_id={current_user.id} job_id={job.id} "
        f"title='{job.title}' has_content={bool(job.raw_text)} "
        f"has_intelligence={bool(job.parsed_data)}"
    )
    return job


@router.get("/list", response_model=List[JobDescriptionResponse])
def list_jobs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(JobDescription).filter(JobDescription.user_id == current_user.id).order_by(JobDescription.created_at.desc()).all()


@router.get("/{job_id}", response_model=JobDescriptionResponse)
def get_job_description(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a specific job description, strictly verifying candidate ownership (Requirement 12)."""
    job = db.query(JobDescription).filter(JobDescription.id == job_id, JobDescription.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job description not found.")
    return job
