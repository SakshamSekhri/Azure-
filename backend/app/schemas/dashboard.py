from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from backend.app.schemas.skill import SkillMatrixItem, RecommendedActionResponse


class DashboardSummaryResponse(BaseModel):
    student_name: str
    target_role: str
    overall_preparation_score: float  # 0 to 100
    total_skills_tracked: int
    assessed_skills_count: int
    strong_skills_count: int
    weak_skills_count: int
    evidence_count: int
    github_connected: bool
    resume_uploaded: bool
    jd_uploaded: bool
    active_plan_progress_percentage: float
    top_strengths: List[str] = []
    top_gaps: List[str] = []
    recommended_action: RecommendedActionResponse
    skill_matrix: List[SkillMatrixItem] = []
    has_active_plan: bool = False
    plan_id: Optional[int] = None
