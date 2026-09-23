from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CandidateInfo(BaseModel):
    user_id: int
    name: str
    target_role: str
    experience_level: str = "Entry Level"
    college: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None
    github_username: Optional[str] = None


class ProfileSkillItem(BaseModel):
    canonical_id: str
    display_name: str
    category: str
    claimed: bool = False
    claimed_level: Optional[str] = None
    demonstrated_level: Optional[str] = None
    confidence: str = "Low"  # High, Medium, Low, None
    assessment_score: Optional[float] = None
    evidence_count: int = 0
    github_evidence: bool = False
    importance: Optional[str] = None  # "Required", "Preferred", etc.


class PlacementProfileSchema(BaseModel):
    """Central normalized candidate representation (Requirement 3).
    Unifies Resume, JD, GitHub evidence, and Assessment performance into a single source of truth.
    """
    candidate: CandidateInfo
    claimed_skills: List[ProfileSkillItem] = []
    verified_skills: List[ProfileSkillItem] = []
    required_skills: List[ProfileSkillItem] = []
    preferred_skills: List[ProfileSkillItem] = []
    skill_gaps: List[ProfileSkillItem] = []
    projects: List[Any] = []
    experience: List[Any] = []
    education: List[Any] = []
    certifications: List[Any] = []
    github_evidence: List[Dict[str, Any]] = []
    assessment_history: List[Dict[str, Any]] = []
    skill_scores: Dict[str, float] = {}  # canonical_id -> latest score percentage
    weak_topics: List[str] = []
    active_resume_id: Optional[int] = None
    active_jd_id: Optional[int] = None
    has_resume: bool = False
    has_jd: bool = False
