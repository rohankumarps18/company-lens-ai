import re
import httpx
from bs4 import BeautifulSoup
from typing import Optional
from app.providers.base import BaseProvider
from app.schemas.signal import SignalCreate
from pydantic import HttpUrl


class WebsiteProvider(BaseProvider):
    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    async def extract(self, company_id: int, website: str) -> Optional[SignalCreate]:
        target_url = website.rstrip("/")
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(target_url, headers=headers)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            meta_desc = ""
            desc_tag = soup.find("meta", attrs={"name": re.compile(r"description", re.I)}) or soup.find(
                "meta", attrs={"property": re.compile(r"og:description", re.I)}
            )
            if desc_tag and desc_tag.get("content"):
                meta_desc = desc_tag["content"].strip()

            title = soup.title.string.strip() if soup.title and soup.title.string else ""

            headings = [
                h.get_text(strip=True)
                for h in soup.find_all(["h1", "h2", "h3"])
                if h.get_text(strip=True)
            ][:10]

            nav_links = []
            for a in soup.find_all("a", href=True):
                text = a.get_text(strip=True)
                if text and len(text) < 40:
                    nav_links.append({"text": text, "href": a["href"]})
            nav_links = nav_links[:15]

            data = {
                "title": title,
                "meta_description": meta_desc,
                "headings": headings,
                "nav_links": nav_links,
            }

            confidence = 0.85 if meta_desc else 0.5

            return SignalCreate(
                company_id=company_id,
                signal_type="website_metadata",
                value=data,
                source_url=HttpUrl(target_url),
                extraction_method="http_html_parse",
                confidence=confidence,
            )
        except Exception as e:
            return SignalCreate(
                company_id=company_id,
                signal_type="website_metadata",
                value={"error": str(e)},
                source_url=HttpUrl(target_url),
                extraction_method="http_html_parse",
                confidence=0.0,
            )