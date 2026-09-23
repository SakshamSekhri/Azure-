from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.resume import Resume
from backend.app.schemas.resume import ResumeResponse, ResumeAnalysisRequest
from backend.app.services.resume_service import ResumeService

router = APIRouter()


@router.post("/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload resume file (PDF, DOCX, TXT). Text is extracted and stored. AI is NOT called automatically."""
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(contents) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")

    resume = ResumeService.upload_resume(
        db=db,
        user_id=current_user.id,
        file_bytes=contents,
        filename=file.filename or "resume.pdf"
    )
    return resume


@router.post("/analyze", response_model=ResumeResponse)
def analyze_resume(
    request: ResumeAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Explicitly triggered by 'Analyze Resume' button. Invokes AI Gateway or cached analysis."""
    resume = ResumeService.analyze_resume(
        db=db,
        user_id=current_user.id,
        resume_id=request.resume_id,
        force_refresh=request.force_refresh
    )
    return resume


@router.get("/latest", response_model=ResumeResponse)
def get_latest_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from backend.app.core.logging import logger
    resume = (
        db.query(Resume)
        .filter(Resume.user_id == current_user.id)
        .order_by(Resume.version.desc(), Resume.id.desc())
        .first()
    )
    if not resume:
        logger.info(f"[RESUME GET_LATEST] candidate_id={current_user.id} resume_found=False")
        raise HTTPException(status_code=404, detail="No resume found on file.")

    logger.info(
        f"[RESUME GET_LATEST] candidate_id={current_user.id} resume_id={resume.id} "
        f"version={resume.version} filename='{resume.filename}' has_content={bool(resume.raw_text)} "
        f"has_intelligence={bool(resume.parsed_data)}"
    )
    return resume


@router.get("/list", response_model=List[ResumeResponse])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.version.desc()).all()


@router.get("/{resume_id}", response_model=ResumeResponse)
def get_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve a specific resume file, strictly verifying candidate ownership (Requirement 12)."""
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume
