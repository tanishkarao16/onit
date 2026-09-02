from fastapi.testclient import TestClient
import json
import os

from app.main import app
from app.api import cases
from app.models.case import Case as CaseModel, CaseStatus
from app.db.database import SessionLocal

client = TestClient(app)


def test_process_insufficient_case():
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Insufficient",
            description="Missing identity",
            status=CaseStatus.CREATED,
        )
        db.add(case)
        db.commit()
        db.refresh(case)

        resp = client.post(f"/cases/{case.id}/process")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["case"]["status"] == "NEEDS_INFORMATION"
        assert isinstance(data["case"]["missing_information"], list)
    finally:
        db.close()


def test_process_end_to_end_with_research(monkeypatch):
    db = SessionLocal()

    try:
        case = CaseModel(
            title="Flight refund",
            description="Passenger requests refund",
            status=CaseStatus.EVIDENCE_READY,
            passenger="Tanishka Rao",
            booking_reference="SKR8F2",
            airline="Sakura Airways",
            cancellation_date="September 1, 2026",
            amount="¥52,800",
            requested_resolution="Full refund",
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        # Provide fake SERPAPI key and monkeypatch serpapi.search to return sample items
        monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")

        def fake_search(q, api_key, num_results=5):
            return [
                {"title": "Sakura Airways refund policy", "snippet": "Policy says refunds are due", "source": "sakura.com", "link": "https://sakura.com/policy"}
            ]

        monkeypatch.setattr("app.integrations.serpapi.search", fake_search)

        resp = client.post(f"/cases/{case.id}/process")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["case"]["status"] in ("AWAITING_APPROVAL", "PLANNING")
        assert "decision" in data
        assert "plan" in data
        assert isinstance(data["evidence"], list)

    finally:
        db.close()
