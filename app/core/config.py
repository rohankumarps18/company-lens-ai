import os
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_default_credentials() -> str:
    if os.path.exists("credentials.json"):
        with open("credentials.json", "r", encoding="utf-8") as f:
            return f.read()
    return ""


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_KEY: str = "local-dev-key-change-in-production"
    PORT: int = 8000

    DATABASE_URL: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"

    GOOGLE_SHEET_ID: str = "1j7MfaHg6ASOCj9g1ErHEpQkKOJhYytFMZ3V8L-VrVsg"
    GOOGLE_SERVICE_ACCOUNT_JSON: str = get_default_credentials()

    POLL_INTERVAL_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
if not settings.GOOGLE_SERVICE_ACCOUNT_JSON and os.path.exists(
    "credentials.json"
):
    settings.GOOGLE_SERVICE_ACCOUNT_JSON = get_default_credentials()
if not settings.GOOGLE_SHEET_ID:
    settings.GOOGLE_SHEET_ID = "1j7MfaHg6ASOCj9g1ErHEpQkKOJhYytFMZ3V8L-VrVsg"
