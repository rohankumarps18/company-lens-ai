from typing import Optional
from playwright.async_api import async_playwright
from app.providers.base import BaseProvider
from app.schemas.signal import SignalCreate
from pydantic import HttpUrl


class BrowserProvider(BaseProvider):
    def __init__(self, timeout_ms: int = 15000):
        self.timeout_ms = timeout_ms

    async def extract(self, company_id: int, website: str) -> Optional[SignalCreate]:
        target_url = website.rstrip("/")
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                )
                page = await context.new_page()

                await page.goto(
                    target_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout_ms,
                )
                await page.wait_for_timeout(2000)

                raw_rendered_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                clean_text = " ".join(raw_rendered_text.split())[:3000]

                cta_buttons = await page.eval_on_selector_all(
                    "button, a.btn, a.button, a[role='button']",
                    """elements => elements
                        .map(e => e.innerText.trim())
                        .filter(t => t.length > 0 && t.length < 35)""",
                )

                extracted_data = {
                    "rendered_text_snippet": clean_text,
                    "cta_buttons": list(dict.fromkeys(cta_buttons))[:10],
                    "status": "success",
                }

                await context.close()
                await browser.close()

                return SignalCreate(
                    company_id=company_id,
                    signal_type="browser_dom_content",
                    value=extracted_data,
                    source_url=HttpUrl(target_url),
                    extraction_method="playwright_dom",
                    confidence=0.9 if clean_text else 0.4,
                )

        except Exception as e:
            return SignalCreate(
                company_id=company_id,
                signal_type="browser_dom_content",
                value={"error": str(e), "status": "failed"},
                source_url=HttpUrl(target_url),
                extraction_method="playwright_dom",
                confidence=0.0,
            )