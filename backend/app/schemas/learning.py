from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
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
