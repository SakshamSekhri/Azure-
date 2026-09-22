from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON, Float
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class AIOperation(Base):
    __tablename__ = "ai_operations"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    operation_type = Column(String(50), nullable=False, index=True)  # RESUME_ANALYSIS, JOB_ANALYSIS, etc.
    prompt_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    request_metadata = Column(JSON, nullable=True)
    response_json = Column(JSON, nullable=True)
    tokens_used = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="SUCCESS", nullable=False)  # SUCCESS, FAILED, CACHED
    duration_ms = Column(Float, default=0.0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    user = relationship("User", back_populates="ai_operations")
