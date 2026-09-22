import time
import uuid
from typing import Dict, Any, Type, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.config.settings import settings
from backend.app.models.ai_operation import AIOperation
from backend.app.ai.ai_cache import generate_prompt_hash, check_cache
from backend.app.ai.ai_logger import log_ai_request_start, log_ai_request_finish, log_ai_request_error
from backend.app.ai.foundry_agent import foundry_client
from backend.app.core.logging import logger


class AIGateway:
    """Centralized AI Gateway enforcing strict credit control, SHA-256 prompt hashing,
    Pydantic schema validation, and complete operation auditing.
    """

    @classmethod
    def execute(
        cls,
        db: Session,
        user_id: Optional[int] = None,
        operation_type: str = "",
        payload: Dict[str, Any] = None,
        response_model: Type[BaseModel] = None,
        force_refresh: bool = False
    ) -> BaseModel:
        start_time = time.time()
        op_id = str(uuid.uuid4())
        prompt_hash = generate_prompt_hash(operation_type, payload)

        log_ai_request_start(op_id, operation_type, user_id)

        # 1. Credit Control Cache Lookup (Disabled for assessment question generation so every assessment is fresh)
        if settings.AI_CACHE_ENABLED and not force_refresh and operation_type != "ASSESSMENT_QUESTION_GENERATION":
            cached_entry = check_cache(db, prompt_hash)
            if cached_entry and cached_entry.response_json:
                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"AI Cache Hit! Serving cached response for op_type={operation_type} hash={prompt_hash[:12]}...")

                # Audit record for the cached request
                audit_record = AIOperation(
                    operation_id=op_id,
                    user_id=user_id,
                    operation_type=operation_type,
                    prompt_hash=prompt_hash,
                    request_metadata={"cached_from_op_id": cached_entry.operation_id},
                    response_json=cached_entry.response_json,
                    tokens_used=0,  # Zero new tokens consumed!
                    status="CACHED",
                    duration_ms=duration_ms,
                    error_message=None
                )
                db.add(audit_record)
                db.commit()

                log_ai_request_finish(op_id, operation_type, user_id, duration_ms, "CACHED", 0, cache_hit=True)
                return response_model.model_validate(cached_entry.response_json)

        # 2. Forward to Azure AI Foundry Agent Client
        try:
            result_model, tokens_used, status_flag = foundry_client.execute_operation(
                operation_type=operation_type,
                payload=payload,
                response_model=response_model
            )
            duration_ms = (time.time() - start_time) * 1000

            # 3. Store in Audit & Cache Database
            audit_record = AIOperation(
                operation_id=op_id,
                user_id=user_id,
                operation_type=operation_type,
                prompt_hash=prompt_hash,
                request_metadata={"status_flag": status_flag},
                response_json=result_model.model_dump(),
                tokens_used=tokens_used,
                status=status_flag,
                duration_ms=duration_ms,
                error_message=None
            )
            db.add(audit_record)
            db.commit()

            log_ai_request_finish(op_id, operation_type, user_id, duration_ms, status_flag, tokens_used, cache_hit=False)
            return result_model

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            err_msg = f"{type(e).__name__}: {str(e)}"
            log_ai_request_error(op_id, operation_type, user_id, err_msg)

            # Store failed audit
            audit_record = AIOperation(
                operation_id=op_id,
                user_id=user_id,
                operation_type=operation_type,
                prompt_hash=prompt_hash,
                request_metadata={"error": err_msg},
                response_json=None,
                tokens_used=0,
                status="FAILED",
                duration_ms=duration_ms,
                error_message=err_msg
            )
            db.add(audit_record)
            db.commit()

            raise e
