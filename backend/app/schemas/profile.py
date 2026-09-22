from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from backend.app.schemas.resume import ResumeSummary
from backend.app.schemas.job import JobSummary


class ProfileBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    college: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None
    target_role: str = Field(default="Full Stack Developer")
    experience_level: str = Field(default="Entry Level")
    github_username: Optional[str] = None


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    college: Optional[str] = None
    degree: Optional[str] = None
    graduation_year: Optional[int] = None
    target_role: Optional[str] = None
    experience_level: Optional[str] = None
    github_username: Optional[str] = None


class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    active_resume: Optional[ResumeSummary] = None
    active_job: Optional[JobSummary] = None

    class Config:
        from_attributes = True
