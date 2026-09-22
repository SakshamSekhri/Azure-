from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from backend.app.models.evidence import Evidence
from backend.app.models.skill import StudentSkill, Skill


class EvidenceService:
    @staticmethod
    def add_evidence(
        db: Session,
        user_id: int,
        type: str,
        source: str,
        title: str,
        description: Optional[str] = None,
        url: Optional[str] = None,
        evidence_strength: float = 0.5,
        skill_id: Optional[int] = None,
        skill_name: Optional[str] = None,
        metadata_json: Optional[Dict[str, Any]] = None
    ) -> Evidence:
        # If skill_name provided but skill_id not, look up or create skill
        if not skill_id and skill_name:
            skill = db.query(Skill).filter(Skill.name.ilike(skill_name.strip())).first()
            if skill:
                skill_id = skill.id

        evidence = Evidence(
            user_id=user_id,
            skill_id=skill_id,
            type=type,
            source=source,
            title=title,
            description=description,
            url=url,
            evidence_strength=evidence_strength,
            metadata_json=metadata_json or {}
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        # Update StudentSkill evidence count
        if skill_id:
            student_skill = db.query(StudentSkill).filter(
                StudentSkill.user_id == user_id,
                StudentSkill.skill_id == skill_id
            ).first()
            if student_skill:
                count = db.query(Evidence).filter(
                    Evidence.user_id == user_id,
                    Evidence.skill_id == skill_id
                ).count()
                student_skill.evidence_count = count
                student_skill.last_updated = datetime.now(timezone.utc)
                db.commit()

        return evidence
