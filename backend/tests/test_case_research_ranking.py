import os
from app.services.case_research import research_case
from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseResearch


def test_research_ranking(monkeypatch):
    # create a fake serpapi response with mixed sources
    def fake_search(q, api_key, num_results=5):
        # return items in arbitrary order
        return [
            {"title": "Local news on refunds", "snippet": "Some article", "source": "localnews.com", "link": "https://localnews.com/article"},
            {"title": "Sakura Airways official policy", "snippet": "Policy text", "source": "sakuraairways.com", "link": "https://sakuraairways.com/policy"},
            {"title": "Government passenger rights", "snippet": "Law text", "source": "transport.gov", "link": "https://transport.gov/refund-guidance"},
            {"title": "IATA guidance", "snippet": "IATA notes", "source": "iata.org", "link": "https://iata.org/guidance"},
            {"title": "Opinion blog", "snippet": "opinion", "source": "blog.example.com", "link": "https://blog.example.com/post"},
        ]

    monkeypatch.setenv("SERPAPI_API_KEY", "fake-key")
    monkeypatch.setattr("app.integrations.serpapi.search", fake_search)

    db = SessionLocal()

    # create a minimal case
    case = CaseModel(
        title="Flight refund",
        description="Passenger requests refund",
        status="EVIDENCE_READY",
        passenger="Tanishka Rao",
        booking_reference="SKR8F2",
        airline="Sakura Airways",
    )

    db.add(case)
    db.commit()
    db.refresh(case)

    results = research_case(db, case)

    # Expect government first, then airline, then IATA, then local news, then blog
    urls = [r.url for r in results]
    assert any("transport.gov" in (u or "") for u in urls[:1])
    assert any("sakuraairways.com" in (u or "") for u in urls[:2])
    assert any("iata.org" in (u or "") for u in urls[:3])

    # cleanup
    db.query(CaseResearch).filter(CaseResearch.case_id == case.id).delete()
    db.delete(case)
    db.commit()
    db.close()
