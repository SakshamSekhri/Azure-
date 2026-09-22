from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class AssessmentQuestion(Base):
    """Stores every AI-generated question after generation (Requirement 16).
    The database stores questions AFTER AI generation and is NEVER a source of predefined questions.
    """
    __tablename__ = "assessment_questions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    options = Column(JSON, nullable=False)  # List of 4 strings
    correct_answer = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    skill = Column(String(100), nullable=True, index=True)
    topic = Column(String(100), nullable=True)
    concept = Column(String(100), nullable=True)
    difficulty = Column(String(50), default="Intermediate", nullable=False)
    why_the_question_is_relevant = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    assessment = relationship("Assessment", back_populates="questions")
    answers = relationship("AssessmentAnswer", back_populates="question_rel", cascade="all, delete-orphan")
