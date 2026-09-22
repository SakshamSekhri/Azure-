from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.evidence import Evidence
from backend.app.schemas.evidence import EvidenceResponse, EvidenceCreate
from backend.app.services.evidence_service import EvidenceService

router = APIRouter()


@router.get("", response_model=List[EvidenceResponse])
def get_evidences(
    skill_id: Optional[int] = None,
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Evidence).filter(Evidence.user_id == current_user.id)
    if skill_id:
        q = q.filter(Evidence.skill_id == skill_id)
    if type:
        q = q.filter(Evidence.type == type)
    
    evs = q.order_by(Evidence.created_at.desc()).all()
    results = []
    for e in evs:
        results.append(EvidenceResponse(
            id=e.id,
            user_id=e.user_id,
            skill_id=e.skill_id,
            skill_name=e.skill.name if e.skill else None,
            type=e.type,
            source=e.source,
            title=e.title,
            description=e.description,
            url=e.url,
            evidence_strength=e.evidence_strength,
            metadata_json=e.metadata_json,
            created_at=e.created_at
        ))
    return results


@router.post("", response_model=EvidenceResponse)
def create_evidence(
    ev_in: EvidenceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ev = EvidenceService.add_evidence(
        db=db,
        user_id=current_user.id,
        type=ev_in.type,
        source=ev_in.source,
        title=ev_in.title,
        description=ev_in.description,
        url=ev_in.url,
        evidence_strength=ev_in.evidence_strength,
        skill_id=ev_in.skill_id,
        metadata_json=ev_in.metadata_json
    )
    return EvidenceResponse(
        id=ev.id,
        user_id=ev.user_id,
        skill_id=ev.skill_id,
        skill_name=ev.skill.name if ev.skill else None,
        type=ev.type,
        source=ev.source,
        title=ev.title,
        description=ev.description,
        url=ev.url,
        evidence_strength=ev.evidence_strength,
        metadata_json=ev.metadata_json,
        created_at=ev.created_at
    )
