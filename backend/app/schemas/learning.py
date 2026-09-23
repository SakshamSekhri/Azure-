from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field
from backend.app.schemas.ai import RAGCitation


class LearningPlanGenerateRequest(BaseModel):
    target_role: Optional[str] = None
    force_refresh: bool = False


class LearningActivityResponse(BaseModel):
    id: int
    day_number: int
    topic: str
    skill_name: str
    activity_type: str
    resource_url: Optional[str] = None
    resource_description: Optional[str] = None
    completed: bool
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LearningPlanDetailResponse(BaseModel):
    id: int
    user_id: int
    target_role: str
    duration_days: int
    status: str
    summary: Optional[str] = None
    generated_at: datetime
    activities: List[LearningActivityResponse]
    completion_percentage: float = 0.0

    class Config:
        from_attributes = True


class LearningActivityToggleRequest(BaseModel):
    activity_id: int
    completed: bool


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    topic: Optional[str] = None
    skill: Optional[str] = None


class GroundedRAGResponse(BaseModel):
    question: str
    answer: str
    grounded: bool
    citations: List[RAGCitation]
    confidence: str


class ImprovementPlanItem(BaseModel):
    id: str
    skill: str
    topic: str
    current_score: float = 0.0
    target_score: float = 80.0
    priority: str = "HIGH"  # HIGH, MEDIUM, LOW
    reason: str
    status: str = "Not Started"  # Not Started, In Progress, Mastered
    progress: float = 0.0  # 0 to 100
    recommended_action: str = "Practice"  # Practice, Learn, Assess

    @computed_field
    @property
    def skill_name(self) -> str:
        return self.skill

    @computed_field
    @property
    def topic_name(self) -> str:
        return self.topic

    @computed_field
    @property
    def progress_percentage(self) -> float:
        return self.progress

    @computed_field
    @property
    def actions(self) -> List[str]:
        return ["learn", "practice", "assess"]


class PersonalizedImprovementPlanResponse(BaseModel):
    target_role: str
    target_company: Optional[str] = None
    active_items: List[ImprovementPlanItem] = []
    mastered_items: List[ImprovementPlanItem] = []
    total_items: int = 0
    overall_progress_percentage: float = 0.0
    active_plan_summary: Optional[str] = None
    activities: List[LearningActivityResponse] = []

    @computed_field
    @property
    def items(self) -> List[ImprovementPlanItem]:
        return self.active_items + self.mastered_items

    @computed_field
    @property
    def high_priority_count(self) -> int:
        return sum(1 for it in self.active_items if it.priority == "HIGH")

    @computed_field
    @property
    def medium_priority_count(self) -> int:
        return sum(1 for it in self.active_items if it.priority == "MEDIUM")

    @computed_field
    @property
    def low_priority_count(self) -> int:
        return sum(1 for it in self.active_items if it.priority == "LOW")

    @computed_field
    @property
    def mastered_count(self) -> int:
        return len(self.mastered_items)

