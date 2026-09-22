from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.schemas.github import GitHubConnectRequest, GitHubAnalysisResponse
from backend.app.services.github_service import GitHubService

router = APIRouter()


@router.post("/connect", response_model=GitHubAnalysisResponse)
def connect_github(
    req: GitHubConnectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Analyze public GitHub profile with bounded requests, map supporting evidence to skills."""
    return GitHubService.analyze_user_github(
        db=db,
        user_id=current_user.id,
        username=req.username
    )
