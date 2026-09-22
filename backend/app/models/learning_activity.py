from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class LearningActivity(Base):
    __tablename__ = "learning_activities"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    day_number = Column(Integer, nullable=False)  # 1 to 7
    topic = Column(String(255), nullable=False)
    skill_name = Column(String(100), nullable=False)
    activity_type = Column(String(50), default="theory", nullable=False)  # theory, practice, quiz, project
    resource_url = Column(String(500), nullable=True)
    resource_description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    plan = relationship("LearningPlan", back_populates="activities")
