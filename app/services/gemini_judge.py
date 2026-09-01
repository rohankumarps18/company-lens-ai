# app/services/gemini_judge.py
from typing import List
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.signal import SignalRead
from app.schemas.verdict import Verdict


class GeminiJudgeService:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def evaluate_signals(
        self,
        company_name: str,
        website: str,
        signals: List[SignalRead],
    ) -> Verdict:
        """
        Evaluates the public signals collected for a company and returns a validated structured Verdict.
        """
        if not self.client:
            return Verdict(
                fit="unknown",
                confidence=0.0,
                reasoning="Gemini API Client is not configured. Missing GEMINI_API_KEY.",
                follow_up_question="Can valid API credentials be provided in the environment?",
            )

        signal_evidence = [
            {
                "signal_type": s.signal_type,
                "confidence": s.confidence,
                "data": s.value,
                "extraction_method": s.extraction_method,
            }
            for s in signals
        ]

        system_instruction = (
            "You are a rigorous investment and market evaluation judge. "
            "Evaluate whether the target company has a strong product-market fit, technical viability, "
            "and hiring intent based ONLY on the provided public evidence signals. "
            "Reason strictly from the provided evidence without inventing or hallucinating facts. "
            "If signals are sparse, failed, or missing, state that clearly in your reasoning and lower the confidence score. "
            "Return your evaluation strictly matching the structured output schema."
        )

        prompt = f"""
Target Company: {company_name}
Target Website: {website}

Collected Independent Evidence Signals:
{signal_evidence}

Provide a structured evaluation with:
- fit: 'high', 'medium', 'low', or 'unknown'
- confidence: float between 0.0 and 1.0 (reflecting signal completeness)
- reasoning: grounded synthesis citing only the supplied evidence
- follow_up_question: one targeted question to resolve remaining uncertainty
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=Verdict,
                    temperature=0.1,
                ),
            )
            return Verdict.model_validate_json(response.text)
        except Exception as e:
            return Verdict(
                fit="unknown",
                confidence=0.0,
                reasoning=f"LLM evaluation reasoning failed: {str(e)}",
                follow_up_question="Can the pipeline retry evaluating this company record?",
            )