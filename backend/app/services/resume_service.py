from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
from datetime import datetime, timezone

from backend.app.models.resume import Resume
from backend.app.models.skill import Skill, StudentSkill
from backend.app.models.evidence import Evidence
from backend.app.schemas.ai import ResumeAnalysisResponse
from backend.app.ai.ai_gateway import AIGateway
from backend.app.utils.text_extractor import extract_text_from_file, compute_file_hash
from backend.app.core.logging import logger
from backend.app.services.skill_service import SkillService


class ResumeService:
    @staticmethod
    def upload_resume(db: Session, user_id: int, file_bytes: bytes, filename: str) -> Resume:
        """Extract text, compute hash, and save resume record."""
        extracted_text = extract_text_from_file(file_bytes, filename)
        file_hash = compute_file_hash(file_bytes)

        # Check existing version
        latest_resume = (
            db.query(Resume)
            .filter(Resume.user_id == user_id)
            .order_by(Resume.version.desc())
            .first()
        )
        new_version = (latest_resume.version + 1) if latest_resume else 1

        # Check if identical hash was previously analyzed by this user
        existing_analyzed = (
            db.query(Resume)
            .filter(Resume.user_id == user_id, Resume.file_hash == file_hash, Resume.parsed_data.isnot(None))
            .first()
        )
        parsed_data = existing_analyzed.parsed_data if existing_analyzed else None

        resume = Resume(
            user_id=user_id,
            filename=filename,
            raw_text=extracted_text,
            file_hash=file_hash,
            version=new_version,
            parsed_data=parsed_data,
            uploaded_at=datetime.now(timezone.utc)
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)

        # If we had existing analysis, populate skills right away without calling AI
        if parsed_data:
            ResumeService._sync_claimed_skills(db, user_id, resume)

        return resume

    @staticmethod
    def analyze_resume(db: Session, user_id: int, resume_id: int, force_refresh: bool = False) -> Resume:
        """Triggered explicitly by 'Analyze Resume' button."""
        resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == user_id).first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found.")

        # Re-use already parsed data if present and force_refresh is False
        if resume.parsed_data and not force_refresh:
            logger.info(f"Resume {resume_id} already has parsed data. Reusing cached result.")
            ResumeService._sync_claimed_skills(db, user_id, resume)
            return resume

        payload = {
            "resume_id": resume.id,
            "filename": resume.filename,
            "raw_text": resume.raw_text
        }

        # Invoke AI Gateway with strict Pydantic validation
        analysis_result: ResumeAnalysisResponse = AIGateway.execute(
            db=db,
            user_id=user_id,
            operation_type="RESUME_ANALYSIS",
            payload=payload,
            response_model=ResumeAnalysisResponse,
            force_refresh=force_refresh
        )

        resume.parsed_data = analysis_result.model_dump()
        db.commit()
        db.refresh(resume)

        # Register claimed skills and project evidence
        ResumeService._sync_claimed_skills(db, user_id, resume)
        return resume

    @staticmethod
    def _sync_claimed_skills(db: Session, user_id: int, resume: Resume):
        if not resume.parsed_data:
            return

        skills_list = resume.parsed_data.get("skills", [])
        seen_skill_ids = set()
        for item in skills_list:
            skill_name = item.get("name", "").strip()
            category = item.get("category", "Programming")
            claimed_level = item.get("claimed_level", "Intermediate")
            if not skill_name:
                continue

            # Standardize or insert canonical Skill
            skill = SkillService.get_or_create_skill(db, skill_name, category)
            if not skill or not skill.id:
                continue

            if skill.id in seen_skill_ids:
                continue
            seen_skill_ids.add(skill.id)

            # Insert or update StudentSkill
            student_skill = db.query(StudentSkill).filter(
                StudentSkill.user_id == user_id,
                StudentSkill.skill_id == skill.id
            ).first()

            if not student_skill:
                student_skill = StudentSkill(
                    user_id=user_id,
                    skill_id=skill.id,
                    claimed_level=claimed_level,
                    is_claimed=1,
                    confidence="Low",  # Claimed but unassessed
                    evidence_count=1
                )
                db.add(student_skill)
            else:
                student_skill.claimed_level = claimed_level
                student_skill.is_claimed = 1

            db.flush()

            # Create Resume Evidence
            existing_ev = db.query(Evidence).filter(
                Evidence.user_id == user_id,
                Evidence.skill_id == skill.id,
                Evidence.type == "Resume",
                Evidence.source == resume.filename
            ).first()

            if not existing_ev:
                ev = Evidence(
                    user_id=user_id,
                    skill_id=skill.id,
                    type="Resume",
                    source=resume.filename,
                    title=f"Claimed in Resume ({resume.filename})",
                    description=f"Listed with proficiency '{claimed_level}'",
                    evidence_strength=0.4
                )
                db.add(ev)
                db.flush()

        # Also store Projects as general Evidence
        projects = resume.parsed_data.get("projects", [])
        seen_projects = set()
        for proj in projects:
            proj_name = proj.get("name", "Project").strip()
            if not proj_name or proj_name in seen_projects:
                continue
            seen_projects.add(proj_name)

            existing_proj_ev = db.query(Evidence).filter(
                Evidence.user_id == user_id,
                Evidence.type == "Project",
                Evidence.title == proj_name
            ).first()
            if not existing_proj_ev:
                p_ev = Evidence(
                    user_id=user_id,
                    type="Project",
                    source="Resume",
                    title=proj_name,
                    description=proj.get("description", ""),
                    evidence_strength=0.7,
                    metadata_json=proj
                )
                db.add(p_ev)
                db.flush()

        db.commit()
