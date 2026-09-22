import hashlib
import json
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from backend.app.models.ai_operation import AIOperation
from backend.app.core.logging import logger


def generate_prompt_hash(operation_type: str, payload: Dict[str, Any]) -> str:
    """Generate deterministic SHA-256 hash for operation type, agent version, and payload."""
    from backend.app.config.settings import settings
    agent_version = getattr(settings, "FOUNDRY_AGENT_VERSION", "4")
    serialized = json.dumps(payload, sort_keys=True, default=str)
    raw_key = f"{operation_type}:{agent_version}:{serialized}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


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
