from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class VerdictModel(Base):
    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    fit = Column(String(32), nullable=False)
    confidence = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    follow_up_question = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="verdicts")