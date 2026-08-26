import os

from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseActivity, CaseResearch, CaseStatus
from app.services.case_research import research_case


def test_research_missing_api_key(monkeypatch):
    db = SessionLocal()

    # ensure key is not set
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)

    try:
        case = CaseModel(
            title="Missing key test",
            description="No key",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        try:
            research_case(db=db, case=case)
            assert False, "Expected ValueError for missing API key"
        except ValueError as exc:
            assert "Missing SERPAPI_API_KEY" in str(exc)

    finally:
        db.close()


def test_research_api_failure_records_activity(monkeypatch):
    db = SessionLocal()

    monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")

    def failing_search(query, api_key, num_results=5):
        raise RuntimeError("SerpApi down")

    monkeypatch.setattr("app.integrations.serpapi.search", failing_search)

    try:
        case = CaseModel(
            title="Failure test",
            description="API fails",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        try:
            research_case(db=db, case=case)
            assert False, "Expected ValueError on SerpApi failure"
        except ValueError:
            # ensure RESEARCH_FAILED activity was recorded
            activities = (
                db.query(CaseActivity)
                .filter(CaseActivity.case_id == case.id)
                .order_by(CaseActivity.id.asc())
                .all()
            )

            # Should have at least the started and failed events
            types = [a.event_type for a in activities]
            assert "RESEARCH_STARTED" in types
            assert "RESEARCH_FAILED" in types

    finally:
        db.close()


def test_generic_organization_names_are_ignored(monkeypatch):
    db = SessionLocal()

    monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")

    captured: list[str] = []

    def capture_search(q, api_key, num_results=5):
        captured.append(q)
        return []

    monkeypatch.setattr("app.integrations.serpapi.search", capture_search)

    try:
        case = CaseModel(
            title="Test case with generic org",
            description="Refund requested",
            organization="abc",
            airline="",
            status=CaseStatus.EVIDENCE_READY,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        # Should not raise; captured queries should not include the literal 'abc' as a primary term
        research_case(db=db, case=case)

        assert len(captured) > 0
        assert not any(" abc" in (q.lower()) or q.lower().startswith("abc") for q in captured)

    finally:
        db.close()
