import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.signal import Signal
from app.models.verdict import VerdictModel
from app.models.pipeline_run import PipelineRun
from app.schemas.signal import SignalRead
from app.providers.website_provider import WebsiteProvider
from app.providers.hiring_provider import HiringProvider
from app.providers.browser_provider import BrowserProvider
from app.services.sheets_service import GoogleSheetsService
from app.services.gemini_judge import GeminiJudgeService

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(
        self,
        sheets_service: Optional[GoogleSheetsService] = None,
        judge_service: Optional[GeminiJudgeService] = None,
    ):
        self.sheets_service = sheets_service or GoogleSheetsService()
        self.judge_service = judge_service or GeminiJudgeService()
        self.providers = [
            WebsiteProvider(),
            HiringProvider(),
            BrowserProvider(),
        ]

    async def _collect_signals_for_company(self, company_id: int, website: str) -> List[SignalRead]:
        tasks = [provider.extract(company_id=company_id, website=website) for provider in self.providers]
        extracted_signals = await asyncio.gather(*tasks, return_exceptions=True)

        valid_signals = []
        for res in extracted_signals:
            if isinstance(res, Exception):
                logger.error(f"Provider extraction failed for company {company_id}: {res}")
            elif res is not None:
                valid_signals.append(res)

        return valid_signals

    async def process_single_company(
        self,
        db: Session,
        company_name: str,
        website: str,
        source_row_id: Optional[int] = None,
        run_id: Optional[int] = None,
    ) -> bool:
        company = db.query(Company).filter(Company.website == website).first()
        if not company:
            company = Company(
                name=company_name,
                website=website,
                source_row_id=source_row_id,
            )
            db.add(company)
            db.commit()
            db.refresh(company)

        now_utc = datetime.now(timezone.utc).isoformat()
        try:
            # 1. Collect Signals
            signal_schemas = await self._collect_signals_for_company(company.id, company.website)
            saved_signal_models = []

            for sig in signal_schemas:
                sig_record = Signal(
                    company_id=company.id,
                    signal_type=sig.signal_type,
                    value=sig.value,
                    source_url=str(sig.source_url),
                    extraction_method=sig.extraction_method,
                    confidence=sig.confidence,
                )
                db.add(sig_record)
                saved_signal_models.append(sig_record)

            db.commit()

            # Refresh signals with DB IDs
            signals_for_judge = [
                SignalRead(
                    id=s.id,
                    company_id=s.company_id,
                    signal_type=s.signal_type,
                    value=s.value,
                    source_url=str(s.source_url),
                    extraction_method=s.extraction_method,
                    confidence=s.confidence,
                    collected_at=s.collected_at.isoformat() if s.collected_at else now_utc,
                )
                for s in saved_signal_models
            ]

            # 2. LLM Evaluation
            verdict = await self.judge_service.evaluate_signals(
                company_name=company.name,
                website=company.website,
                signals=signals_for_judge,
            )

            # 3. Store Verdict in DB
            verdict_record = VerdictModel(
                company_id=company.id,
                fit=verdict.fit,
                confidence=verdict.confidence,
                reasoning=verdict.reasoning,
                follow_up_question=verdict.follow_up_question,
            )
            db.add(verdict_record)
            db.commit()

            # 4. Write back to Google Sheets if source_row_id is present
            if source_row_id:
                self.sheets_service.update_row_verdict(
                    row_id=source_row_id,
                    status="completed",
                    fit=verdict.fit,
                    confidence=verdict.confidence,
                    reasoning=verdict.reasoning,
                    follow_up_question=verdict.follow_up_question or "",
                    processed_at=now_utc,
                    error="",
                )

            return True

        except Exception as e:
            logger.error(f"Error executing pipeline for {company_name}: {e}")
            # Roll back so a failed company doesn't leave the session's
            # transaction aborted for the rest of a multi-company
            # run_pipeline() batch (Postgres refuses further commands on
            # an aborted transaction until it's rolled back).
            db.rollback()
            if source_row_id:
                self.sheets_service.update_row_verdict(
                    row_id=source_row_id,
                    status="failed",
                    fit="unknown",
                    confidence=0.0,
                    reasoning="",
                    follow_up_question="",
                    processed_at=now_utc,
                    error=str(e),
                )
            return False

    async def run_pipeline(self, db: Session, trigger_type: str = "manual") -> PipelineRun:
        pipeline_run = PipelineRun(
            trigger_type=trigger_type,
            status="running",
            companies_processed=0,
            companies_failed=0,
        )
        db.add(pipeline_run)
        db.commit()
        db.refresh(pipeline_run)

        unprocessed_rows = self.sheets_service.get_unprocessed_rows()
        processed_count = 0
        failed_count = 0

        for row in unprocessed_rows:
            success = await self.process_single_company(
                db=db,
                company_name=row["company_name"],
                website=row["website"],
                source_row_id=row["source_row_id"],
                run_id=pipeline_run.id,
            )
            if success:
                processed_count += 1
            else:
                failed_count += 1

        pipeline_run.status = "completed" if failed_count == 0 else "partial_success"
        pipeline_run.companies_processed = processed_count
        pipeline_run.companies_failed = failed_count
        pipeline_run.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(pipeline_run)
        return pipeline_run