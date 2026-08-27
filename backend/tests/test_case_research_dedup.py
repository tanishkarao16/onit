import os

from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseResearch, CaseStatus
from app.services.case_research import research_case


def test_research_dedup_by_url(monkeypatch):
    db = SessionLocal()

    monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")

    # two identical results (same url)
    def fake_search(q, api_key, num_results=5):
        return [
            {"title": "Policy A", "snippet": "info", "link": "https://a.example/policy", "source": "a.example"}
        ]

    monkeypatch.setattr("app.integrations.serpapi.search", fake_search)

    try:
        case = CaseModel(title="Dedup test", description="dedup test", status=CaseStatus.EVIDENCE_READY)
        db.add(case)
        db.commit()
        db.refresh(case)

        # first run persists
        res1 = research_case(db=db, case=case)
        stored = db.query(CaseResearch).filter(CaseResearch.case_id == case.id).all()
        assert len(stored) == len(res1) >= 1

        # second run with same results should not create duplicates
        res2 = research_case(db=db, case=case)
        stored2 = db.query(CaseResearch).filter(CaseResearch.case_id == case.id).all()
        assert len(stored2) == len(stored)

    finally:
        db.close()


def test_research_allows_different_urls(monkeypatch):
    db = SessionLocal()

    monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")

    # first run returns URL A, second run returns URL B (same title)
    def fake_search_a(q, api_key, num_results=5):
        return [{"title": "Policy X", "snippet": "info1", "link": "https://x.example/policy1", "source": "x.example"}]

    def fake_search_b(q, api_key, num_results=5):
        return [{"title": "Policy X", "snippet": "info2", "link": "https://x.example/policy2", "source": "x.example"}]

    # first run uses fake_search_a
    monkeypatch.setattr("app.integrations.serpapi.search", fake_search_a)

    try:
        case = CaseModel(title="Different URL test", description="different url test", status=CaseStatus.EVIDENCE_READY)
        db.add(case)
        db.commit()
        db.refresh(case)

        research_case(db=db, case=case)
        stored = db.query(CaseResearch).filter(CaseResearch.case_id == case.id).all()
        assert len(stored) == 1

        # run again with different search behavior -> should persist additional row
        monkeypatch.setattr("app.integrations.serpapi.search", fake_search_b)
        research_case(db=db, case=case)
        stored2 = db.query(CaseResearch).filter(CaseResearch.case_id == case.id).all()
        assert len(stored2) == 2

    finally:
        db.close()


def test_research_dedup_without_url_uses_source_title(monkeypatch):
    db = SessionLocal()

    monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")

    # results without link; dedupe by source+title
    def fake_search(q, api_key, num_results=5):
        return [{"title": "NoLink Policy", "snippet": "info", "source": "nolink.example"}]

    monkeypatch.setattr("app.integrations.serpapi.search", fake_search)

    try:
        case = CaseModel(title="No URL test", description="no url test", status=CaseStatus.EVIDENCE_READY)
        db.add(case)
        db.commit()
        db.refresh(case)

        research_case(db=db, case=case)
        stored = db.query(CaseResearch).filter(CaseResearch.case_id == case.id).all()
        assert len(stored) == 1

        # run again identical -> should not duplicate
        research_case(db=db, case=case)
        stored2 = db.query(CaseResearch).filter(CaseResearch.case_id == case.id).all()
        assert len(stored2) == 1

    finally:
        db.close()
