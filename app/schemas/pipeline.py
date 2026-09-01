from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class PipelineRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: Literal["running", "completed", "failed", "partial_success"]
    companies_processed: int = Field(default=0, ge=0)
    companies_failed: int = Field(default=0, ge=0)
    trigger_type: Optional[str] = "manual"
    error: Optional[str] = None


PipelineRunResponse = PipelineRunRead


class PipelineTriggerResponse(BaseModel):
    message: str
    run_id: Optional[int] = None
    status: Literal["accepted", "already_running"]


class EvaluateCompanyRequest(BaseModel):
    name: str
    website: HttpUrl


class CompanyEvaluationResponse(BaseModel):
    company_name: str
    website: str
    fit: str
    confidence: float
    reasoning: str
    follow_up_question: Optional[str] = None
    signals_count: int