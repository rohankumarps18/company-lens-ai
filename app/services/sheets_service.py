import json
import logging
from typing import List, Dict, Any, Optional
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleSheetsService:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(
        self,
        sheet_id: Optional[str] = None,
        service_account_info: Optional[str] = None,
    ):
        self.sheet_id = sheet_id or settings.GOOGLE_SHEET_ID
        self.service_account_raw = service_account_info or settings.GOOGLE_SERVICE_ACCOUNT_JSON
        self.service = self._init_service()

    def _init_service(self):
        if not self.service_account_raw or not self.sheet_id:
            logger.warning("Google Sheets credentials or Sheet ID missing in configuration.")
            return None
        try:
            info = json.loads(self.service_account_raw)
            credentials = Credentials.from_service_account_info(info, scopes=self.SCOPES)
            return build("sheets", "v4", credentials=credentials, cache_discovery=False)
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets API client: {e}")
            return None

    def get_unprocessed_rows(self) -> List[Dict[str, Any]]:
        """
        Reads rows from sheet A:I and filters for rows where status is empty or pending.
        Returns a list of dicts with keys: source_row_id, company_name, website.
        """
        if not self.service:
            logger.warning("Google Sheets client unavailable. Returning empty list.")
            return []

        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.sheet_id, range="A:I").execute()
            rows = result.get("values", [])

            if not rows or len(rows) < 2:
                return []

            headers = [h.strip().lower() for h in rows[0]]
            records = []

            for idx, row in enumerate(rows[1:], start=2):
                padded_row = row + [""] * (len(headers) - len(row))
                row_dict = dict(zip(headers, padded_row))

                status = row_dict.get("status", "").strip().lower()
                if status in ["", "pending", "unprocessed"]:
                    name = row_dict.get("company_name", "").strip()
                    website = row_dict.get("website", "").strip()
                    if name and website:
                        records.append({
                            "source_row_id": idx,
                            "company_name": name,
                            "website": website,
                        })

            return records
        except Exception as e:
            logger.error(f"Error fetching rows from Google Sheets: {e}")
            return []

    def update_row_verdict(
        self,
        row_id: int,
        status: str,
        fit: str,
        confidence: float,
        reasoning: str,
        follow_up_question: str,
        processed_at: str,
        error: Optional[str] = "",
    ) -> bool:
        """
        Updates columns C to I for a specific row index.
        """
        if not self.service:
            return False

        range_name = f"C{row_id}:I{row_id}"
        values = [[
            status,
            fit,
            f"{confidence:.2f}",
            reasoning,
            follow_up_question,
            processed_at,
            error or "",
        ]]

        body = {"values": values}
        try:
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                body=body,
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating row {row_id} in Google Sheets: {e}")
            return False