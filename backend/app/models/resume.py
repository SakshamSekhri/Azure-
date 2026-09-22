from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from backend.app.core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for caching analysis
    version = Column(Integer, default=1, nullable=False)
    parsed_data = Column(JSON, nullable=True)  # Structured extracted skills, projects, etc.
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="resumes")
