from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.pipeline_run import PipelineRun
from app.models.company import Company
from app.models.verdict import VerdictModel
from app.schemas.pipeline import (
    EvaluateCompanyRequest,
    PipelineRunRead,
    CompanyEvaluationResponse,
)
from app.services.orchestrator import PipelineOrchestrator

router = APIRouter(prefix="/api/v1", tags=["Pipeline"])
orchestrator = PipelineOrchestrator()


@router.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    return {"status": "healthy", "service": "company-lens-ai"}


@router.post("/pipeline/run", response_model=PipelineRunRead)
async def trigger_pipeline_run(db: Session = Depends(get_db)):
    """Triggers an ingestion & evaluation run for all unprocessed rows in Google Sheets."""
    run_record = await orchestrator.run_pipeline(db=db, trigger_type="manual_api")
    return run_record


@router.post("/evaluate", response_model=CompanyEvaluationResponse)
async def evaluate_single_company(
    payload: EvaluateCompanyRequest,
    db: Session = Depends(get_db),
):
    """Enriches and evaluates an ad-hoc company without requiring a Google Sheets entry."""
    normalized_url = str(payload.website).rstrip("/")
    success = await orchestrator.process_single_company(
        db=db,
        company_name=payload.name,
        website=normalized_url,
        source_row_id=None,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enrich and evaluate target company.",
        )

    company = db.query(Company).filter(Company.website == normalized_url).first()
    verdict = (
        db.query(VerdictModel)
        .filter(VerdictModel.company_id == company.id)
        .order_by(VerdictModel.id.desc())
        .first()
        if company
        else None
    )

    return CompanyEvaluationResponse(
        company_name=company.name if company else payload.name,
        website=company.website if company else normalized_url,
        fit=verdict.fit if verdict else "unknown",
        confidence=verdict.confidence if verdict else 0.0,
        reasoning=verdict.reasoning if verdict else "",
        follow_up_question=verdict.follow_up_question if verdict else None,
        signals_count=len(company.signals) if company else 0,
    )


@router.get("/runs", response_model=List[PipelineRunRead])
def get_pipeline_runs(limit: int = 20, db: Session = Depends(get_db)):
    return (
        db.query(PipelineRun)
        .order_by(PipelineRun.id.desc())
        .limit(limit)
        .all()
    )