# tests/test_api.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.main import app
from app.models.company import Company
from app.models.verdict import VerdictModel

# Use StaticPool so all connections share the same in-memory SQLite database
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "company-lens-ai"}


@pytest.mark.asyncio
async def test_evaluate_single_company_endpoint():
    with patch("app.api.routes.orchestrator.process_single_company", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = True

        target_url = "https://testorg.example"

        with TestingSessionLocal() as db:
            comp = Company(name="Test Org", website=target_url)
            db.add(comp)
            db.commit()
            db.refresh(comp)

            verdict = VerdictModel(
                company_id=comp.id,
                fit="high",
                confidence=0.95,
                reasoning="Strong alignment with AI infra market.",
                follow_up_question="Do you offer private cloud installations?",
            )
            db.add(verdict)
            db.commit()

        response = client.post(
            "/api/v1/evaluate",
            json={"name": "Test Org", "website": target_url},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Test Org"
        assert data["fit"] == "high"
        assert data["confidence"] == 0.95