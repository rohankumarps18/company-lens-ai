# app/schemas/signal.py
from datetime import datetime
from typing import Any, Dict, Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SignalBase(BaseModel):
    signal_type: Literal["website_metadata", "hiring_signals", "browser_dom_content"]
    value: Dict[str, Any] = Field(..., description="Structured payload extracted by provider")
    source_url: HttpUrl
    extraction_method: Literal["http_json", "http_html_parse", "playwright_dom"]
    confidence: float = Field(..., ge=0.0, le=1.0)


class SignalCreate(SignalBase):
    company_id: int


class SignalRead(SignalBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    collected_at: datetime
