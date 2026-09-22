from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime, JSON
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
    answers_json = Column(JSON, nullable=False)  # User's submitted answers
    result_summary_json = Column(JSON, nullable=True)  # Strengths, weaknesses, gaps, improvement plan
    completed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="assessment_attempts")
    assessment = relationship("Assessment", back_populates="attempts")
