from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    
    score_percentage = Column(Float, nullable=False)  # e.g. 85.0
    total_questions = Column(Integer, nullable=False)
    correct_count = Column(Integer, nullable=False)
    attempt_number = Column(Integer, default=1, nullable=False)  # Explicit attempt 1, 2, 3... (Requirement 23)
    duration_seconds = Column(Integer, nullable=True)  # Elapsed time in seconds
    analysis_status = Column(String(50), default="pending", nullable=False, index=True)  # pending, completed, failed
    answers_json = Column(JSON, nullable=False)  # User's submitted answers
    result_summary_json = Column(JSON, nullable=True)  # Strengths, weaknesses, gaps, improvement plan
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="assessment_attempts")
    assessment = relationship("Assessment", back_populates="attempts")
    answers_rel = relationship("AssessmentAnswer", back_populates="attempt", cascade="all, delete-orphan")
