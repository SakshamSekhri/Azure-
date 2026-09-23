import hashlib
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone

from backend.app.models.job import JobDescription
from backend.app.models.skill import Skill, StudentSkill
from backend.app.schemas.ai import JobAnalysisResponse
from backend.app.ai.ai_gateway import AIGateway
from backend.app.core.logging import logger
from backend.app.services.skill_service import SkillService


class JobService:
    @staticmethod
    def create_job_description(
        db: Session,
        user_id: int,
        title: str,
        raw_text: str,
        company: Optional[str] = None
    ) -> JobDescription:
        text_hash = hashlib.sha256(raw_text.strip().encode("utf-8")).hexdigest()

        # Check existing with same hash for user
        existing = (
            db.query(JobDescription)
            .filter(JobDescription.user_id == user_id, JobDescription.text_hash == text_hash)
            .first()
        )
        if existing:
            return existing

        job = JobDescription(
            user_id=user_id,
            title=title,
            company=company,
            raw_text=raw_text,
            text_hash=text_hash,
            parsed_data=None,
            created_at=datetime.now(timezone.utc)
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    @staticmethod
    def analyze_job_description(
        db: Session,
        user_id: int,
        job_id: int,
        force_refresh: bool = False
    ) -> JobDescription:
        job = db.query(JobDescription).filter(
            JobDescription.id == job_id,
            JobDescription.user_id == user_id
        ).first()

        if not job:
            raise HTTPException(status_code=404, detail="Job description not found.")

        if job.parsed_data and not force_refresh:
            logger.info(f"Job Description {job_id} already has parsed data. Reusing cached analysis.")
            JobService._sync_required_skills(db, user_id, job)
            return job

        payload = {
            "job_id": job.id,
            "title": job.title,
            "company": job.company or "",
            "raw_text": job.raw_text
        }

        analysis_result: JobAnalysisResponse = AIGateway.execute(
            db=db,
            user_id=user_id,
            operation_type="JOB_ANALYSIS",
            payload=payload,
            response_model=JobAnalysisResponse,
            force_refresh=force_refresh
        )

        job.parsed_data = analysis_result.model_dump()
        db.commit()
        db.refresh(job)

        JobService._sync_required_skills(db, user_id, job)
        return job

    @staticmethod
    def _sync_required_skills(db: Session, user_id: int, job: JobDescription):
        if not job.parsed_data:
            return

        all_req_skills = job.parsed_data.get("required_skills", []) + job.parsed_data.get("preferred_skills", [])
        for item in all_req_skills:
            skill_name = item.get("name", "").strip()
            category = item.get("category", "Programming")
            if not skill_name:
                continue

            # Standardize or insert canonical Skill
            skill = SkillService.get_or_create_skill(db, skill_name, category)

            student_skill = db.query(StudentSkill).filter(
                StudentSkill.user_id == user_id,
                StudentSkill.skill_id == skill.id
            ).first()

            if not student_skill:
                student_skill = StudentSkill(
                    user_id=user_id,
                    skill_id=skill.id,
                    is_required_by_jd=1,
                    confidence="Low",
                    evidence_count=0
                )
                db.add(student_skill)
            else:
                student_skill.is_required_by_jd = 1

        db.commit()

    @staticmethod
    def get_active_target_job(
        db: Session,
        user_id: int,
        job_id: Optional[int] = None
    ) -> Optional[JobDescription]:
        """Fetch the single authoritative active target job for a candidate.
        If job_id is provided, verify it belongs to user_id.
        Otherwise, fetch the latest JobDescription for the user.
        """
        if job_id:
            return (
                db.query(JobDescription)
                .filter(JobDescription.id == job_id, JobDescription.user_id == user_id)
                .first()
            )
        return (
            db.query(JobDescription)
            .filter(JobDescription.user_id == user_id)
            .order_by(JobDescription.id.desc())
            .first()
        )
