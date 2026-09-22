from datetime import datetime
from typing import Optional, Any, Dict
from pydantic import BaseModel, computed_field


class ResumeSummary(BaseModel):
    id: int
    filename: str
    version: int
    uploaded_at: datetime
    has_content: bool = True
    has_intelligence: bool = False
    file_hash: Optional[str] = None

    class Config:
        from_attributes = True


class ResumeResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_hash: str
    version: int
    raw_text: Optional[str] = None
    parsed_data: Optional[Dict[str, Any]] = None
    uploaded_at: datetime

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


class ResumeAnalysisRequest(BaseModel):
    resume_id: int
    force_refresh: bool = False
