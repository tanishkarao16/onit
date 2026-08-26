import os

from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity, CaseResearch, CaseStatus
from app.services.case_research import research_case


def test_research_case_persists_results_and_activity(monkeypatch):
    db = SessionLocal()

    # Provide a fake API key
    monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")

    # Mock serpapi.search
    def fake_search(query, api_key, num_results=5):
        return [
            {
                "title": "Example Airways refund policy",
                "snippet": "Passengers are entitled to...",
                "link": "https://example.com/policy",
                "source": "example.com",
            }
        ]

    monkeypatch.setattr("app.integrations.serpapi.search", fake_search)

    try:
        case = CaseModel(
            title="Flight cancellation refund",
            description="Passenger is requesting a full refund.",
            passenger="Alex Morgan",
            booking_reference="ABC123",
            organization="Example Airways",
            airline="Example Airways",
            amount="Y120,000",
            refund_received=False,
            requested_resolution="Refund the full Y120,000",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        results = research_case(db=db, case=case)

        assert len(results) >= 1

        assert results[0].source == "example.com"
        assert "refund" in results[0].title.lower()

        assert case.status == CaseStatus.EVIDENCE_READY

        stored = (
            db.query(CaseResearch)
            .filter(CaseResearch.case_id == case.id)
            .all()
        )

        assert len(stored) >= 1
        assert stored[0].url == "https://example.com/policy"
        assert "This source" in stored[0].summary or "official" in stored[0].summary.lower()

        activities = (
            db.query(CaseActivity)
            .filter(CaseActivity.case_id == case.id)
            .order_by(
                CaseActivity.created_at.asc(),
                CaseActivity.id.asc(),
            )
            .all()
        )

        assert len(activities) == 2

        assert activities[0].event_type == "RESEARCH_STARTED"
        assert activities[1].event_type == "RESEARCH_COMPLETED"

    finally:
        db.close()
