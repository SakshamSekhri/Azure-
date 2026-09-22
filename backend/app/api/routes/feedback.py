from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.feedback import Feedback

router = APIRouter()


@router.get("/list")
def list_feedback(
    type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    q = db.query(Feedback).filter(Feedback.user_id == current_user.id)
    if type:
        q = q.filter(Feedback.type == type)
    return q.order_by(Feedback.generated_at.desc()).all()
