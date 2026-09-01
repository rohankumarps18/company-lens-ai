# app/schemas/company.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class CompanyBase(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    website: HttpUrl
    source_row_id: int = Field(..., ge=2, description="Row index inside Google Sheets (2+)")


class CompanyCreate(CompanyBase):
    pass


class CompanyRead(CompanyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    created_at: datetime
    updated_at: datetime
