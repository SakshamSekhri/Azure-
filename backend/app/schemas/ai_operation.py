from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class AIOperationResponse(BaseModel):
    id: int
    operation_id: str
    user_id: Optional[int] = None
    operation_type: str
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    prompt_hash: str
    status: str
    input_tokens: int = 0
    output_tokens: int = 0
    tokens_used: int = 0
    duration_ms: float = 0.0
    cache_hit: bool = False
    estimated_cost: float = 0.0
    error_message: Optional[str] = None
    created_at: datetime
    request_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class AIUsageSummary(BaseModel):
    total_operations: int
    successful_calls: int
    cached_calls: int
    failed_calls: int
    cache_hit_rate_percentage: float
    total_tokens_used: int
    estimated_cost_usd: float
    operations_by_type: Dict[str, int]
    recent_operations: List[AIOperationResponse]
