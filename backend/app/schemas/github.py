from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class GitHubConnectRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)


class GitHubRepoInfo(BaseModel):
    name: str
    full_name: str
    description: Optional[str] = None
    html_url: str
    language: Optional[str] = None
    languages: Dict[str, int] = {}
    topics: List[str] = []
    stargazers_count: int = 0
    forks_count: int = 0
    updated_at: Optional[str] = None
    has_readme: bool = False
    readme_snippet: Optional[str] = None


class GitHubAnalysisResponse(BaseModel):
    username: str
    total_repos_inspected: int
    primary_languages: List[str]
    detected_frameworks: List[str]
    detected_skills: List[str]
    evidence_created_count: int
    repos: List[GitHubRepoInfo]
    summary: str
