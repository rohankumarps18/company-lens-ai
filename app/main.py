import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import Base, engine, SessionLocal
from app.api.routes import router
from app.services.orchestrator import PipelineOrchestrator

logger = logging.getLogger("company_lens_ai")
orchestrator = PipelineOrchestrator()


async def sheets_polling_worker(interval_seconds: int = 300):
    """Background loop that periodically checks Google Sheets for new unprocessed entries."""
    await asyncio.sleep(5)  # Warmup delay
    while True:
        try:
            logger.info("Polling Google Sheets for unprocessed companies...")
            with SessionLocal() as db:
                await orchestrator.run_pipeline(db=db, trigger_type="scheduled_cron")
        except Exception as e:
            logger.error(f"Error during background polling: {e}")
        await asyncio.sleep(interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables
    Base.metadata.create_all(bind=engine)

    # Spawn background worker
    task = asyncio.create_task(
        sheets_polling_worker(interval_seconds=settings.POLL_INTERVAL_SECONDS)
    )
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Company Lens AI",
    version="1.0.0",
    description="Automated investment signal pipeline with Google Sheets, Playwright, and Gemini evaluation.",
    lifespan=lifespan,
)

app.include_router(router)