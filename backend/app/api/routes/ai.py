from typing import List, Dict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.database import get_db
from backend.app.api.deps import get_current_user
from backend.app.models.user import User
from backend.app.models.ai_operation import AIOperation
from backend.app.schemas.ai_operation import AIOperationResponse, AIUsageSummary

router = APIRouter()


@router.get("/usage", response_model=AIUsageSummary)
def get_ai_usage_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieve AI operation auditing, cache hits, token usage, and cost estimation."""
    ops = db.query(AIOperation).filter(AIOperation.user_id == current_user.id).all()
    total_ops = len(ops)

    successful = sum(1 for op in ops if op.status in ["SUCCESS", "LIVE_FOUNDRY"])
    cached = sum(1 for op in ops if op.status == "CACHED")
    failed = sum(1 for op in ops if op.status == "FAILED")
    total_tokens = sum(op.tokens_used for op in ops)

    cache_hit_rate = round((cached / total_ops * 100.0), 1) if total_ops > 0 else 0.0

    # Operations by type
    ops_by_type: Dict[str, int] = {}
    for op in ops:
        ops_by_type[op.operation_type] = ops_by_type.get(op.operation_type, 0) + 1

    # Azure AI Foundry GPT-5-mini estimated blended price: ~$0.50 per 1M tokens ($0.0000005 per token)
    estimated_cost = round(total_tokens * 0.0000005, 4)

    recent_ops = (
        db.query(AIOperation)
        .filter(AIOperation.user_id == current_user.id)
        .order_by(AIOperation.created_at.desc())
        .limit(20)
        .all()
    )

    return AIUsageSummary(
        total_operations=total_ops,
        successful_calls=successful,
        cached_calls=cached,
        failed_calls=failed,
        cache_hit_rate_percentage=cache_hit_rate,
        total_tokens_used=total_tokens,
        estimated_cost_usd=estimated_cost,
        operations_by_type=ops_by_type,
        recent_operations=recent_ops
    )


@router.get("/logs", response_model=List[AIOperationResponse])
def get_ai_logs(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(AIOperation)
        .filter(AIOperation.user_id == current_user.id)
        .order_by(AIOperation.created_at.desc())
        .limit(limit)
        .all()
    )
