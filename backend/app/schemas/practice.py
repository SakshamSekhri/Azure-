from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, computed_field


class PracticeGenerateRequest(BaseModel):
    skill: str = Field(..., min_length=1, description="Target skill name or canonical ID (e.g. Docker, Python, SQL)")
    topic: Optional[str] = Field(default=None, description="Optional specific topic within the skill (e.g. Multi-stage builds, Indexing)")
    num_questions: int = Field(default=5, ge=1, le=10, description="Number of practice questions to generate")
    difficulty: Optional[str] = Field(default=None, description="Adaptive difficulty override (Beginner, Intermediate, Advanced)")


class FocusedAssessmentGenerateRequest(BaseModel):
    skill: str = Field(..., min_length=1, description="Target skill name or canonical ID")
    topic: Optional[str] = Field(default=None, description="Optional specific topic within the skill")
    num_questions: int = Field(default=10, ge=5, le=15, description="Number of focused assessment questions")
    difficulty: Optional[str] = Field(default=None, description="Adaptive difficulty override")


class TopicPerformanceItem(BaseModel):
    topic: str
    skill_name: str
    canonical_skill_id: str
    questions_attempted: int = 0
    correct_count: int = 0
    accuracy_percentage: Optional[float] = None
    status: str = "Unattempted"  # Mastered (>=80%), In Progress (60-79%), Needs Practice (<60%), Unattempted
    weak_concepts: List[str] = []
    last_practiced_at: Optional[datetime] = None


class SkillFocusDetailResponse(BaseModel):
    skill_name: str
    canonical_id: str
    category: str
    jd_importance: str  # Required, Preferred, Missing, Bonus
    current_score: Optional[float] = None
    demonstrated_level: str = "Unassessed"
    confidence: str = "None"
    total_practice_attempts: int = 0
    topics: List[TopicPerformanceItem] = []
    recommended_action: Dict[str, Any] = {}

    @computed_field
    @property
    def topic_breakdown(self) -> List[TopicPerformanceItem]:
        return self.topics
