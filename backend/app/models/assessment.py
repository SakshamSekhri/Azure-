from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Assessment(Base):
    __tablename__ = "assessments"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    job_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    role = Column(String(255), nullable=True)
    difficulty = Column(String(50), default="Intermediate", nullable=False)  # Beginner, Intermediate, Advanced
    question_count = Column(Integer, default=5, nullable=False)
    status = Column(String(50), default="pending", nullable=False)  # pending, completed
    questions_json = Column(JSON, nullable=False)  # List of questions with options, correct answer, explanation, skill/topic
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    candidate = relationship("User", back_populates="assessments")
    job = relationship("JobDescription")
    skill = relationship("Skill", back_populates="assessments")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    answers = relationship("AssessmentAnswer", back_populates="assessment", cascade="all, delete-orphan")
    attempts = relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")
