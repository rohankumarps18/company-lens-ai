import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.providers.browser_provider import BrowserProvider


@pytest.mark.asyncio
async def test_browser_provider_success():
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value="Autonomous Intelligence Platform for Modern Enterprise")
    mock_page.eval_on_selector_all = AsyncMock(return_value=["Request Demo", "Start Free Trial"])

    mock_context = AsyncMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()

    mock_browser = AsyncMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright_manager = AsyncMock()
    mock_playwright_manager.chromium.launch = AsyncMock(return_value=mock_browser)

    mock_async_playwright = MagicMock()
    mock_async_playwright.return_value.__aenter__.return_value = mock_playwright_manager
    mock_async_playwright.return_value.__aexit__.return_value = None

    with patch("app.providers.browser_provider.async_playwright", mock_async_playwright):
        provider = BrowserProvider()
        signal = await provider.extract(company_id=10, website="https://example.com")

        assert signal.company_id == 10
        assert signal.signal_type == "browser_dom_content"
        assert signal.extraction_method == "playwright_dom"
        assert signal.confidence == 0.9
        assert "Autonomous Intelligence Platform" in signal.value["rendered_text_snippet"]
        assert "Request Demo" in signal.value["cta_buttons"]


@pytest.mark.asyncio
async def test_browser_provider_timeout_fallback():
    mock_async_playwright = MagicMock()
    mock_async_playwright.return_value.__aenter__.side_effect = Exception("Page navigation timeout")

    with patch("app.providers.browser_provider.async_playwright", mock_async_playwright):
        provider = BrowserProvider(timeout_ms=1000)
        signal = await provider.extract(company_id=11, website="https://nonexistent-site.example")

        assert signal.company_id == 11
        assert signal.confidence == 0.0
        assert signal.value["status"] == "failed"
        assert "Page navigation timeout" in signal.value["error"]