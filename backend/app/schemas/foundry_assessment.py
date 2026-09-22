from pydantic import BaseModel, Field
from typing import Optional, Any, Dict


class AssessmentStartRequest(BaseModel):
    role: str = Field(..., description="Target role (e.g. Backend Developer)")
    job_description: str = Field(..., description="Target job description or requirements")
    resume: str = Field(..., description="Candidate resume text or claimed skills")
    task: Optional[str] = Field(default=None, description="Specific assessment generation task prompt")


class AssessmentStartResponse(BaseModel):
    status: str = "success"
    agent_name: str
    agent_version: str
    response: str
    raw_output: Optional[Any] = None
