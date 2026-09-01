import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import HttpUrl

from app.core.database import Base
from app.models.company import Company
from app.models.signal import Signal
from app.models.verdict import VerdictModel
from app.schemas.verdict import Verdict
from app.schemas.signal import SignalCreate
from app.services.orchestrator import PipelineOrchestrator

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.mark.asyncio
async def test_pipeline_run_success(db_session):
    mock_sheets = MagicMock()
    mock_sheets.get_unprocessed_rows.return_value = [
        {"source_row_id": 2, "company_name": "Acme AI", "website": "https://acme.example"}
    ]
    mock_sheets.update_row_verdict.return_value = True

    mock_judge = MagicMock()
    mock_judge.evaluate_signals = AsyncMock(
        return_value=Verdict(
            fit="high",
            confidence=0.92,
            reasoning="Valid technical stack and hiring intent.",
            follow_up_question="Do you support on-prem deployment?",
        )
    )

    orchestrator = PipelineOrchestrator(sheets_service=mock_sheets, judge_service=mock_judge)

    mock_signal = SignalCreate(
        company_id=1,
        signal_type="website_metadata",
        value={"title": "Acme AI Platform"},
        source_url=HttpUrl("https://acme.example"),
        extraction_method="http_html_parse",
        confidence=0.9,
    )

    for provider in orchestrator.providers:
        provider.extract = AsyncMock(return_value=mock_signal)

    run_record = await orchestrator.run_pipeline(db=db_session, trigger_type="test")

    assert run_record.status == "completed"
    assert run_record.companies_processed == 1
    assert run_record.companies_failed == 0

    # Validate database records
    saved_company = db_session.query(Company).filter(Company.website == "https://acme.example").first()
    assert saved_company is not None
    assert saved_company.name == "Acme AI"

    saved_signals = db_session.query(Signal).filter(Signal.company_id == saved_company.id).all()
    assert len(saved_signals) == 3

    saved_verdict = db_session.query(VerdictModel).filter(VerdictModel.company_id == saved_company.id).first()
    assert saved_verdict is not None
    assert saved_verdict.fit == "high"
    assert saved_verdict.confidence == 0.92

    mock_sheets.update_row_verdict.assert_called_once()