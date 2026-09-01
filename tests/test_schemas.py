import pytest
from pydantic import ValidationError
from app.schemas.verdict import Verdict
from app.schemas.company import CompanyCreate


def test_valid_verdict_schema():
    data = {
        "fit": "high",
        "confidence": 0.92,
        "reasoning": "Company matches criteria based on active AI job postings and stated B2B SaaS target.",
        "follow_up_question": "What is the ARR range?",
    }
    verdict = Verdict(**data)
    assert verdict.fit == "high"
    assert verdict.confidence == 0.92


@pytest.mark.parametrize(
    "invalid_confidence",
    [-0.1, 1.01, 2.0, -10.0],
)
def test_invalid_verdict_confidence_range(invalid_confidence):
    data = {
        "fit": "low",
        "confidence": invalid_confidence,
        "reasoning": "Insufficient signal coverage available on the landing page.",
        "follow_up_question": "Are hiring signals published externally?",
    }
    with pytest.raises(ValidationError):
        Verdict(**data)


def test_invalid_verdict_fit_literal():
    data = {
        "fit": "exceptional",  # Not in high/medium/low/unknown
        "confidence": 0.5,
        "reasoning": "Invalid fit literal test.",
        "follow_up_question": "N/A?",
    }
    with pytest.raises(ValidationError):
        Verdict(**data)


def test_company_create_url_validation():
    with pytest.raises(ValidationError):
        CompanyCreate(
            company_name="Acme Corp",
            website="not-a-valid-url",
            source_row_id=2,
        )

    company = CompanyCreate(
        company_name="Acme Corp",
        website="https://acme.example.com",
        source_row_id=2,
    )
    assert str(company.website) == "https://acme.example.com/"
