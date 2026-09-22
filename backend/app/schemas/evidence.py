from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class EvidenceCreate(BaseModel):
    skill_id: Optional[int] = None
    type: str = Field(..., description="Resume, GitHub, Assessment, Project")
    source: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    evidence_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    metadata_json: Optional[Dict[str, Any]] = None


class EvidenceResponse(BaseModel):
    id: int
    user_id: int
    skill_id: Optional[int] = None
    skill_name: Optional[str] = None
    type: str
    source: str
    title: str
    description: Optional[str] = None
    url: Optional[str] = None
    evidence_strength: float
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
