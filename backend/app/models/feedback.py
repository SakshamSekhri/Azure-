from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # assessment, overall
    source_id = Column(Integer, nullable=True)  # assessment_id or attempt_id
    content = Column(Text, nullable=False)
    strengths_json = Column(JSON, nullable=True)
    weaknesses_json = Column(JSON, nullable=True)
    recommendations_json = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="feedbacks")
