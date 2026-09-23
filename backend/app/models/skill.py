from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, UniqueConstraint, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    canonical_id = Column(String(100), index=True, nullable=True)  # Normalized canonical identifier (e.g. 'react', 'postgresql')
    name = Column(String(100), unique=True, index=True, nullable=False)
    category = Column(String(50), index=True, nullable=False)  # Programming, Framework, Database, etc.
    aliases = Column(JSON, nullable=True)  # Known aliases for this canonical skill
    description = Column(String(255), nullable=True)

    student_skills = relationship("StudentSkill", back_populates="skill", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="skill", cascade="all, delete-orphan")
    evidences = relationship("Evidence", back_populates="skill", cascade="all, delete-orphan")


class StudentSkill(Base):
    __tablename__ = "student_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True)
    
    claimed_level = Column(String(50), nullable=True)  # Beginner, Intermediate, Advanced
    demonstrated_level = Column(String(50), nullable=True)  # Derived from assessment/evidence
    confidence = Column(String(50), default="Low", nullable=False)  # Low, Medium, High
    assessment_score = Column(Float, nullable=True)  # 0.0 to 100.0
    evidence_count = Column(Integer, default=0, nullable=False)
    is_claimed = Column(Integer, default=0, nullable=False)  # 1 if in resume, 0 otherwise
    is_required_by_jd = Column(Integer, default=0, nullable=False)  # 1 if in active JD, 0 otherwise
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )

    user = relationship("User", back_populates="student_skills")
    skill = relationship("Skill", back_populates="student_skills")
