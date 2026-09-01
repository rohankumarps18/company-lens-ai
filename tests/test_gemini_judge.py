import pytest
from unittest.mock import MagicMock
from app.services.gemini_judge import GeminiJudgeService
from app.schemas.signal import SignalRead


@pytest.mark.asyncio
async def test_gemini_judge_successful_structured_output():
    judge = GeminiJudgeService(api_key="fake-test-key", model="gemini-2.5-flash")
    judge.client = MagicMock()

    mock_response = MagicMock()
    mock_response.text = (
        '{"fit": "high", "confidence": 0.91, '
        '"reasoning": "Strong hiring signals for AI Engineers and validated product metadata.", '
        '"follow_up_question": "What is their current production model inference infrastructure?"}'
    )
    judge.client.models.generate_content.return_value = mock_response

    signals = [
        SignalRead(
            id=1,
            company_id=10,
            signal_type="website_metadata",
            value={"title": "Cloud Intelligence Inc"},
            source_url="https://cloudintelligence.example",
            extraction_method="http_html_parse",
            confidence=0.85,
            collected_at="2026-09-01T12:00:00Z",
        ),
        SignalRead(
            id=2,
            company_id=10,
            signal_type="hiring_signals",
            value={"detected_roles": {"ai_ml": ["AI Engineer"]}},
            source_url="https://cloudintelligence.example/careers",
            extraction_method="http_html_parse",
            confidence=0.8,
            collected_at="2026-09-01T12:00:00Z",
        ),
    ]

    verdict = await judge.evaluate_signals(
        company_name="Cloud Intelligence Inc",
        website="https://cloudintelligence.example",
        signals=signals,
    )

    assert verdict.fit == "high"
    assert verdict.confidence == 0.91
    assert "Strong hiring signals" in verdict.reasoning
    assert verdict.follow_up_question.startswith("What is")


@pytest.mark.asyncio
async def test_gemini_judge_missing_key_fallback():
    judge = GeminiJudgeService(api_key="", model="gemini-2.5-flash")
    verdict = await judge.evaluate_signals("Acme", "https://example.com", [])

    assert verdict.fit == "unknown"
    assert verdict.confidence == 0.0
    assert "Missing GEMINI_API_KEY" in verdict.reasoning