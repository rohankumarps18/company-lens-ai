import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
from urllib.parse import urljoin
from app.providers.base import BaseProvider
from app.schemas.signal import SignalCreate
from pydantic import HttpUrl


class HiringProvider(BaseProvider):
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout
        self.hiring_paths = ["/careers", "/jobs", "/join-us", "/about/careers"]
        self.target_keywords = {
            "engineering": [
                r"\bsoftware\s+engineer\b",
                r"\bbackend\b",
                r"\bfrontend\b",
                r"\bfullstack\b",
                r"\bdevops\b",
            ],
            "ai_ml": [
                r"\bmachine\s+learning\b",
                r"\bai\s+engineer\b",
                r"\bllm\b",
                r"\bdata\s+scientist\b",
                r"\bresearch\s+scientist\b",
            ],
            "data": [
                r"\bdata\s+engineer\b",
                r"\bdata\s+analyst\b",
                r"\banalytics\s+engineer\b",
            ],
        }

    async def extract(self, company_id: int, website: str) -> Optional[SignalCreate]:
        base_url = website.rstrip("/")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        careers_url = base_url
        careers_html = ""

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for path in self.hiring_paths:
                test_url = urljoin(base_url, path)
                try:
                    resp = await client.get(test_url, headers=headers)
                    if resp.status_code == 200 and len(resp.text.strip()) > 50:
                        careers_url = test_url
                        careers_html = resp.text
                        break
                except Exception:
                    continue

        if not careers_html:
            return SignalCreate(
                company_id=company_id,
                signal_type="hiring_signals",
                value={"careers_page_found": False, "openings": {}},
                source_url=HttpUrl(base_url),
                extraction_method="http_html_parse",
                confidence=0.3,
            )

        soup = BeautifulSoup(careers_html, "html.parser")
        text_content = soup.get_text(separator=" ", strip=True)

        found_categories: Dict[str, List[str]] = {}
        for category, patterns in self.target_keywords.items():
            matches = []
            for pat in patterns:
                found = re.findall(pat, text_content, re.IGNORECASE)
                if found:
                    matches.extend(list(set(found)))
            if matches:
                found_categories[category] = matches

        has_openings = bool(found_categories)

        return SignalCreate(
            company_id=company_id,
            signal_type="hiring_signals",
            value={
                "careers_page_found": True,
                "careers_url": careers_url,
                "detected_roles": found_categories,
                "has_hiring_intent": has_openings,
            },
            source_url=HttpUrl(careers_url),
            extraction_method="http_html_parse",
            confidence=0.8 if has_openings else 0.5,
        )