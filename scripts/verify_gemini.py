"""
Standalone smoke test that makes one REAL call to Gemini using your real
GEMINI_API_KEY from .env. Not part of the pytest suite on purpose - the
test suite should never hit the real API (costs money, needs network,
would make CI flaky). Run this manually whenever you want hard proof the
app is actually talking to Gemini and not silently falling back.

Usage (from the repo root, with .venv activated and a real .env in place):
    python scripts/verify_gemini.py
"""
import asyncio
import sys

sys.path.insert(0, ".")

from app.core.config import settings  # noqa: E402
from app.services.gemini_judge import GeminiJudgeService  # noqa: E402
from app.schemas.signal import SignalRead  # noqa: E402


async def main() -> None:
    if not settings.GEMINI_API_KEY:
        print("FAIL: GEMINI_API_KEY is empty in your loaded settings/.env.")
        print("This script would only prove the fallback path, so stopping here.")
        sys.exit(1)

    print(f"Using model: {settings.GEMINI_MODEL}")
    print(f"API key present: yes (length={len(settings.GEMINI_API_KEY)})")

    judge = GeminiJudgeService()  # real client, pulled from settings

    fake_signals = [
        SignalRead(
            id=1,
            company_id=1,
            signal_type="website_metadata",
            value={"title": "Acme AI", "pricing": "Enterprise, custom quote"},
            source_url="https://acme-ai.example",
            extraction_method="http_html_parse",
            confidence=0.9,
            collected_at="2026-09-02T00:00:00Z",
        ),
        SignalRead(
            id=2,
            company_id=1,
            signal_type="hiring_signals",
            value={"detected_roles": {"ai_ml": ["ML Engineer", "AI Platform Lead"]}},
            source_url="https://acme-ai.example/careers",
            extraction_method="http_html_parse",
            confidence=0.85,
            collected_at="2026-09-02T00:00:00Z",
        ),
    ]

    verdict = await judge.evaluate_signals(
        company_name="Acme AI",
        website="https://acme-ai.example",
        signals=fake_signals,
    )

    print("\n--- Verdict returned ---")
    print(f"fit:                 {verdict.fit}")
    print(f"confidence:          {verdict.confidence}")
    print(f"reasoning:           {verdict.reasoning}")
    print(f"follow_up_question:  {verdict.follow_up_question}")

    # The fallback path always uses these exact strings - if we see them,
    # the real API call did NOT happen, even though the script "succeeded".
    fallback_markers = ("Missing GEMINI_API_KEY", "LLM evaluation reasoning failed")
    if any(marker in verdict.reasoning for marker in fallback_markers):
        print("\nFAIL: this is the fallback verdict, not a real Gemini response.")
        print("Check the reasoning text above for the underlying exception.")
        sys.exit(1)

    print("\nOK: this came from a real Gemini API call.")


if __name__ == "__main__":
    asyncio.run(main())
