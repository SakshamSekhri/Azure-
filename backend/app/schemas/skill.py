from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    description: Optional[str] = None


class SkillResponse(BaseModel):
    id: int
    canonical_id: Optional[str] = None
    name: str
    category: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class StudentSkillResponse(BaseModel):
    id: int
    skill_id: int
    canonical_id: Optional[str] = None
    skill_name: str
    category: str
    claimed_level: Optional[str] = None
    demonstrated_level: Optional[str] = None
    confidence: str
    assessment_score: Optional[float] = None
    evidence_count: int
    is_claimed: bool
    is_required_by_jd: bool
    last_updated: datetime

    class Config:
        from_attributes = True


class SkillMatrixItem(BaseModel):
    skill_id: int
    canonical_id: Optional[str] = None
    skill_name: str
    category: str
    claimed: bool
    github_evidence: bool
    assessment_score: Optional[float] = None
    demonstrated_level: Optional[str] = None
    confidence: str  # "High", "Medium", "Low", "None"
    status: str  # "Ready", "Needs Practice", "Critical Gap", "Unassessed"
    evidence_count: int


class SkillGapResponse(BaseModel):
    target_role: str
    total_skills_tracked: int
    strong_skills: List[str]
    moderate_skills: List[str]
    weak_skills: List[str]
    critical_gaps: List[str]
    matrix: List[SkillMatrixItem]


class RecommendedActionResponse(BaseModel):
    action_type: str  # ASSESSMENT, LEARNING, RESUME, GITHUB, REASSESSMENT
    title: str
    description: str
    reason: str
    skill_name: Optional[str] = None
    topic: Optional[str] = None
    target_route: str


class CandidateJDSkillItem(BaseModel):
    skill_name: str
    category: str
    importance: str = "Required"  # Required, Preferred
    candidate_status: str  # "Evidence Found", "Needs Assessment", "Skill Gap", "Unknown", "Not Relevant"
    evidence_source: Optional[str] = None  # e.g. "Resume", "GitHub", "None"
    assessment_score: Optional[float] = None
    notes: str = ""


class CandidateJDComparisonResponse(BaseModel):
    target_role: str
    total_jd_skills: int
    matched_skills_count: int
    match_percentage: float
    evidence_found: List[str] = []
    needs_assessment: List[str] = []
    skill_gaps: List[str] = []
    unknown: List[str] = []
    items: List[CandidateJDSkillItem] = []
