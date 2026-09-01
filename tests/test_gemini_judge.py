import pytest
from unittest.mock import AsyncMock, patch
from app.services.gemini_judge import GeminiJudgeService
from app.schemas.signal import SignalCreate
from app.schemas.verdict import Verdict

@pytest.mark.asyncio
async def test_gemini_judge_successful_structured_output():
    judge = GeminiJudgeService(api_key="mock-key", model="gemini-3.6-flash")
    
    mock_signals = [
        SignalCreate(
            company_id=1,
            provider="browser",
            signal_type="browser_dom_content",
            value={"text": "Enterprise AI agent platform automating workflows for Fortune 500."},
            source_url="https://enterpriseai.test",
            extraction_method="playwright_dom",
            confidence=0.95,
            raw_data={"text": "Enterprise AI agent platform automating workflows for Fortune 500."}
        )
    ]
    
    expected_verdict = Verdict(
        fit="high",
        confidence=0.92,
        reasoning="Strong enterprise product offering with clear enterprise customer traction.",
        follow_up_question="What is the current annual contract value (ACV) for enterprise deployments?"
    )
    
    with patch.object(judge, "evaluate_signals", new=AsyncMock(return_value=expected_verdict)):
        verdict = await judge.evaluate_signals("Enterprise AI Inc", "https://enterpriseai.test", mock_signals)
        
        assert verdict.fit == "high"
        assert verdict.confidence == 0.92
        assert "enterprise" in verdict.reasoning.lower()
        assert len(verdict.follow_up_question) > 0

@pytest.mark.asyncio
async def test_gemini_judge_missing_key_fallback():
    judge = GeminiJudgeService(api_key="", model="gemini-3.6-flash")
    verdict = await judge.evaluate_signals("Acme", "https://example.com", [])

    assert verdict.fit == "unknown"
    assert verdict.confidence == 0.0
    assert "Missing GEMINI_API_KEY" in verdict.reasoning
