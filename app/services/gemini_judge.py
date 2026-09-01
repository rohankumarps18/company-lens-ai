import json
import logging
from typing import List, Optional
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.signal import SignalCreate
from app.schemas.verdict import Verdict

logger = logging.getLogger(__name__)

class GeminiJudgeService:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.client = None

    async def evaluate_signals(
        self,
        company_name: str,
        website: str,
        signals: List[SignalCreate]
    ) -> Verdict:
        if not self.api_key or not self.client:
            logger.warning("Missing GEMINI_API_KEY. Returning fallback verdict.")
            return Verdict(
                fit="unknown",
                confidence=0.0,
                reasoning="Missing GEMINI_API_KEY configuration.",
                follow_up_question="Can the pipeline retry evaluating this company record?"
            )

        context_signals = []
        for s in signals:
            context_signals.append(f"Provider: {s.provider} | Data: {json.dumps(s.raw_data)}")
        signals_text = "\n".join(context_signals) if context_signals else "No signals extracted."

        prompt = f"""You are an expert investment and business development evaluation judge.
Evaluate the following company based strictly on the provided signals.

Company: {company_name}
Website: {website}

Signals Extracted:
{signals_text}

Provide an objective assessment strictly answering with:
- fit: "high", "medium", "low", or "unknown"
- confidence: float between 0.0 and 1.0
- reasoning: Detailed evidence-based rationale citing specific traction, pricing, or product lines.
- follow_up_question: A targeted discovery question.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=Verdict,
                    temperature=0.2,
                ),
            )
            data = json.loads(response.text)
            return Verdict(**data)
        except Exception as e:
            logger.error(f"Gemini evaluation failed: {e}")
            return Verdict(
                fit="unknown",
                confidence=0.0,
                reasoning=f"LLM evaluation reasoning failed: {str(e)}",
                follow_up_question="Can the pipeline retry evaluating this company record?"
            )
