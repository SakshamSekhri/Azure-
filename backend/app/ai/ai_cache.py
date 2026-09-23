import hashlib
import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from backend.app.models.ai_operation import AIOperation
from backend.app.core.logging import logger


def generate_prompt_hash(
    operation_type: str,
    payload: Dict[str, Any],
    model: Optional[str] = None,
    prompt_version: Optional[str] = None
) -> str:
    """Generate deterministic SHA-256 hash incorporating operation, model, prompt_version, and context hash (Requirement 16).
    Changing prompt_version automatically invalidates incompatible previous cached results.
    """
    from backend.app.config.settings import settings
    from backend.app.ai.prompts import PROMPT_VERSIONS

    selected_model = model or getattr(settings, "FOUNDRY_AGENT_NAME", "PlacementPreparationAgent")
    selected_version = prompt_version or PROMPT_VERSIONS.get(operation_type, PROMPT_VERSIONS.get("DEFAULT", "v1.0"))

    serialized_context = json.dumps(payload, sort_keys=True, default=str)
    context_hash = hashlib.sha256(serialized_context.encode("utf-8")).hexdigest()

    cache_key = f"{operation_type}:{selected_model}:{selected_version}:{context_hash}"
    return hashlib.sha256(cache_key.encode("utf-8")).hexdigest()


def check_cache(db: Session, prompt_hash: str) -> Optional[AIOperation]:
    """Check if a successful operation with the same prompt hash exists."""
    valid_statuses = ["LIVE_FOUNDRY", "SUCCESS"]

    return (
        db.query(AIOperation)
        .filter(
            AIOperation.prompt_hash == prompt_hash,
            AIOperation.status.in_(valid_statuses),
            AIOperation.response_json.isnot(None)
        )
        .order_by(AIOperation.created_at.desc())
        .first()
    )
