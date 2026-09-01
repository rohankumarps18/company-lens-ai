from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, index=True)
    trigger_type = Column(String(32), nullable=False, default="manual")
    status = Column(String(32), nullable=False, default="running")
    companies_processed = Column(Integer, default=0)
    companies_failed = Column(Integer, default=0)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)