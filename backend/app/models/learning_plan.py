from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class LearningPlan(Base):
    __tablename__ = "learning_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_role = Column(String(255), nullable=False)
    duration_days = Column(Integer, default=7, nullable=False)
    status = Column(String(50), default="active", nullable=False)  # active, completed, archived
    summary = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="learning_plans")
    activities = relationship("LearningActivity", back_populates="plan", cascade="all, delete-orphan", order_by="LearningActivity.day_number")
