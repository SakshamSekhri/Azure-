import time
from typing import Dict, Any, Optional
from backend.app.core.logging import logger


def log_ai_request_start(operation_id: str, operation_type: str, user_id: int):
    logger.info(
        f"[AI_GATEWAY_START] op_id={operation_id} type={operation_type} user_id={user_id}"
    )


def log_ai_request_finish(
    operation_id: str,
    operation_type: str,
    user_id: int,
    duration_ms: float,
    status: str,
    tokens_used: int = 0,
    cache_hit: bool = False
):
    logger.info(
        f"[AI_GATEWAY_COMPLETE] op_id={operation_id} type={operation_type} user_id={user_id} "
        f"status={status} cache_hit={cache_hit} duration={duration_ms:.1f}ms tokens={tokens_used}"
    )


def log_ai_request_error(operation_id: str, operation_type: str, user_id: int, error: str):
    logger.error(
        f"[AI_GATEWAY_ERROR] op_id={operation_id} type={operation_type} user_id={user_id} error={error}"
    )
