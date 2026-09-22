from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, Field, computed_field


class JobDescriptionCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    company: Optional[str] = None
    raw_text: str = Field(..., min_length=20)


class JobSummary(BaseModel):
    id: int
    title: str
    company: Optional[str] = None
    exists: bool = True
    has_content: bool = True
    has_intelligence: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class JobDescriptionResponse(BaseModel):
    id: int
    user_id: int
    title: str
    company: Optional[str] = None
    raw_text: str
    parsed_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    @computed_field
    @property
    def has_content(self) -> bool:
        return bool(self.raw_text and self.raw_text.strip())

    @computed_field
    @property
    def has_intelligence(self) -> bool:
        return bool(self.parsed_data)

    class Config:
        from_attributes = True


class JobAnalysisRequest(BaseModel):
    job_id: int
    force_refresh: bool = False
