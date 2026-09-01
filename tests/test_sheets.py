import pytest
import httpx
from unittest.mock import patch, AsyncMock
from app.providers.website_provider import WebsiteProvider
from app.providers.hiring_provider import HiringProvider


@pytest.mark.asyncio
async def test_website_provider_extraction():
    sample_html = """
    <html>
        <head>
            <title>Acme Inc - Automation Platform</title>
            <meta name="description" content="Acme builds infrastructure automation tools." />
        </head>
        <body>
            <h1>Welcome to Acme</h1>
            <h2>Autonomous Operations</h2>
            <a href="/pricing">Pricing</a>
        </body>
    </html>
    """

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = sample_html
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        provider = WebsiteProvider()
        signal = await provider.extract(company_id=1, website="https://acme.example.com")

        assert signal.company_id == 1
        assert signal.signal_type == "website_metadata"
        assert signal.confidence == 0.85
        assert signal.value["title"] == "Acme Inc - Automation Platform"
        assert "Autonomous Operations" in signal.value["headings"]


@pytest.mark.asyncio
async def test_hiring_provider_detection():
    sample_careers_html = """
    <html>
        <body>
            <h1>Careers at Acme</h1>
            <p>We are actively looking for a Software Engineer and an AI Engineer to join our team.</p>
        </body>
    </html>
    """

    mock_resp = AsyncMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = sample_careers_html
    mock_resp.raise_for_status = lambda: None

    with patch("httpx.AsyncClient.get", return_value=mock_resp):
        provider = HiringProvider()
        signal = await provider.extract(company_id=2, website="https://acme.example.com")

        assert signal.company_id == 2
        assert signal.signal_type == "hiring_signals"
        assert signal.value["careers_page_found"] is True
        assert signal.value["has_hiring_intent"] is True
        assert "engineering" in signal.value["detected_roles"]
        assert "ai_ml" in signal.value["detected_roles"]
        assert signal.confidence == 0.8