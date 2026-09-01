from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    signal_type = Column(String(100), nullable=False)
    value = Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    source_url = Column(String(1024), nullable=False)
    extraction_method = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False, default=1.0)
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="signals")