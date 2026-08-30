from fastapi.testclient import TestClient

from app.main import app
from app.api import cases


client = TestClient(app)


def test_parse_case_endpoint(monkeypatch):
    fake_response = {
        "output": {
            "elements": [
                {"role": "Text", "text": "Passenger: Alex Morgan\nBooking reference: ABC123"},
                {"role": "Text", "text": "Airline: Example Airways"},
                {"role": "Text", "text": "Flight cancellation date: August 1, 2026"},
                {"role": "Text", "text": "Amount paid: Y120,000"},
                {"role": "Text", "text": "Refund received: No"},
                {
                    "role": "Text",
                    "text": "Requested resolution:\nRefund the full Y120,000",
                },
                {"role": "ListItem", "text": "- Booking reference: ABC123"},
            ]
        }
    }

    async def fake_parse_document(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(
        cases,
        "parse_document",
        fake_parse_document,
    )

    with open("tests/fixtures/refund_case.pdf", "rb") as document:
        response = client.post(
            "/cases/parse",
            files={
                "file": (
                    "refund_case.pdf",
                    document,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["case"]["passenger"] == "Alex Morgan"
    assert data["case"]["booking_reference"] == "ABC123"
    assert data["case"]["airline"] == "Example Airways"
    assert data["case"]["amount"] == "Y120,000"
    assert data["case"]["refund_received"] is False


def test_parse_and_create_case_persists(monkeypatch):
    fake_response = {
        "output": {
            "elements": [
                {
                    "role": "Text",
                    "text": "Passenger: Alex Morgan\nBooking reference: ABC123",
                },
                {"role": "Text", "text": "Airline: Example Airways"},
                {
                    "role": "Text",
                    "text": "Flight cancellation date: August 1, 2026",
                },
                {"role": "Text", "text": "Amount paid:Y120,000"},
                {"role": "Text", "text": "Refund received: No"},
                {
                    "role": "Text",
                    "text": "Requested resolution:\nRefund the full Y120,000",
                },
                {"role": "ListItem", "text": "- Booking reference: ABC123"},
            ]
        }
    }

    async def fake_parse_document(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(
        cases,
        "parse_document",
        fake_parse_document,
    )

    with open("tests/fixtures/refund_case.pdf", "rb") as document:
        response = client.post(
            "/cases/parse-and-create",
            files={
                "file": (
                    "refund_case.pdf",
                    document,
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["case"]["id"] is not None
    assert data["case"]["passenger"] == "Alex Morgan"
    assert data["case"]["booking_reference"] == "ABC123"
    assert data["case"]["airline"] == "Example Airways"
    assert data["case"]["amount"] == "Y120,000"
    assert data["case"]["refund_received"] is False
    assert data["case"]["status"] == "CREATED"


def test_analyze_case_endpoint_persists_decision():
    create_response = client.post(
        "/cases",
        json={
            "title": "Flight cancellation refund",
            "description": "Passenger is requesting a full refund.",
            "organization": "Example Airways",
            "amount": "Y120,000",
            "currency": "JPY",
        },
    )

    assert create_response.status_code == 200

    case_id = create_response.json()["case"]["id"]

    # Populate the parsed-case fields that the analysis engine uses.
    from app.db.database import SessionLocal
    from app.models.case import Case

    db = SessionLocal()

    try:
        case = db.get(Case, case_id)

        assert case is not None

        case.passenger = "Alex Morgan"
        case.booking_reference = "ABC123"
        case.airline = "Example Airways"
        case.cancellation_date = "August 1, 2026"
        case.refund_received = False
        case.requested_resolution = "Refund the full Y120,000"
        case.supporting_facts = '["Refund received: No"]'

        db.commit()
    finally:
        db.close()

    response = client.post(f"/cases/{case_id}/analyze")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["case"]["id"] == case_id
    assert data["case"]["status"] == "EVIDENCE_READY"

    # ====================================================
    # DECISION
    # ====================================================

    assert data["case"]["issue"] == (
        "Cancelled flight with refund not received"
    )

    assert data["case"]["recommended_action"] == (
        "Verify the passenger's refund eligibility, "
        "contact the airline to request the applicable "
        "refund, and follow up until a response is received."
    )

    assert data["case"]["priority"] == "high"

def test_case_activity_endpoint():
    from app.db.database import SessionLocal
    from app.models.case import Case as CaseModel, CaseActivity, CaseStatus

    db = SessionLocal()

    try:
        case = CaseModel(
            title="Activity test case",
            description="Testing case timeline.",
            status=CaseStatus.CREATED,
        )

        db.add(case)
        db.commit()
        db.refresh(case)

        db.add(
            CaseActivity(
                case_id=case.id,
                event_type="ANALYSIS_STARTED",
                message="ONIT started analyzing the case.",
            )
        )
        db.add(
            CaseActivity(
                case_id=case.id,
                event_type="ANALYSIS_COMPLETED",
                message="ONIT completed analysis.",
            )
        )
        db.commit()

        response = client.get(
            f"/cases/{case.id}/activity"
        )

        assert response.status_code == 200

        data = response.json()

        assert data["status"] == "ok"
        assert len(data["activities"]) == 2
        assert data["activities"][0]["event_type"] == (
            "ANALYSIS_STARTED"
        )
        assert data["activities"][1]["event_type"] == (
            "ANALYSIS_COMPLETED"
        )

    finally:
        db.close()


def test_synthesize_endpoint_success_and_variants():
    from app.db.database import SessionLocal
    from app.models.case import Case as CaseModel, CaseResearch, CaseStatus

    db = SessionLocal()

    try:
        # create a case
        create_response = client.post(
            "/cases",
            json={
                "title": "Synthesis test",
                "description": "Test synthesis",
            },
        )
        assert create_response.status_code == 200
        case_id = create_response.json()["case"]["id"]

        # add authoritative research
        db_case = db.get(CaseModel, case_id)
        db_case.status = CaseStatus.EVIDENCE_READY
        db.commit()

        db.add(
            CaseResearch(
                case_id=case_id,
                source="gov.example",
                title="Official policy",
                summary="Official guidance",
                relevance="high",
                url="https://gov.example/policy",
            )
        )
        db.commit()

        # synthesize
        resp = client.post(f"/cases/{case_id}/synthesize")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["case"]["status"] == "AWAITING_APPROVAL"
        assert data["case"]["approval_required"] is True

        # missing case
        resp2 = client.post("/cases/99999/synthesize")
        assert resp2.status_code == 404

        # insufficient evidence
        create_response2 = client.post(
            "/cases",
            json={
                "title": "Empty evidence",
                "description": "No research",
            },
        )
        cid2 = create_response2.json()["case"]["id"]

        db_case2 = db.get(CaseModel, cid2)
        db_case2.status = CaseStatus.EVIDENCE_READY
        db.commit()

        resp3 = client.post(f"/cases/{cid2}/synthesize")
        assert resp3.status_code == 400

        # non-authoritative evidence leads to awaiting approval
        create_response3 = client.post(
            "/cases",
            json={
                "title": "Generic evidence",
                "description": "Generic source",
            },
        )
        cid3 = create_response3.json()["case"]["id"]
        db_case3 = db.get(CaseModel, cid3)
        db_case3.status = CaseStatus.EVIDENCE_READY
        db.commit()

        db.add(
            CaseResearch(
                case_id=cid3,
                source="example.com",
                title="Blog post",
                summary="Some opinion",
                relevance="low",
                url="https://example.com/article",
            )
        )
        db.commit()

        resp4 = client.post(f"/cases/{cid3}/synthesize")
        assert resp4.status_code == 200
        assert resp4.json()["case"]["status"] == "AWAITING_APPROVAL"

    finally:
        db.close()


def test_synthesize_run_research_triggers_when_missing(monkeypatch):
    from app.db.database import SessionLocal
    from app.models.case import Case as CaseModel, CaseResearch, CaseStatus

    db = SessionLocal()

    try:
        create_response = client.post(
            "/cases",
            json={"title": "Run research", "description": "run research"},
        )
        cid = create_response.json()["case"]["id"]

        # ensure no research exists
        assert db.query(CaseResearch).filter(CaseResearch.case_id == cid).count() == 0

        # monkeypatch the real research_case to add a persisted research row
        def fake_research(*args, **kwargs):
            db_arg = kwargs.get("db") if "db" in kwargs else (args[0] if len(args) > 0 else None)
            case_arg = kwargs.get("case") if "case" in kwargs else (args[1] if len(args) > 1 else None)
            db_arg.add(
                CaseResearch(
                    case_id=case_arg.id,
                    source="gov.example",
                    title="Official policy",
                    summary="Official guidance",
                    relevance="high",
                    url="https://gov.example/policy",
                )
            )
            db_arg.commit()
            return []

        monkeypatch.setattr("app.api.cases.research_case", fake_research)

        resp = client.post(f"/cases/{cid}/synthesize?run_research=true")
        assert resp.status_code == 200
        j = resp.json()
        assert j["case"]["status"] == "AWAITING_APPROVAL"
        assert j["case"]["approval_required"] is True

    finally:
        db.close()


def test_synthesize_run_research_skips_when_exists(monkeypatch):
    from app.db.database import SessionLocal
    from app.models.case import Case as CaseModel, CaseResearch, CaseStatus

    db = SessionLocal()

    try:
        create_response = client.post(
            "/cases",
            json={"title": "Skip research", "description": "has evidence"},
        )
        cid = create_response.json()["case"]["id"]

        # add existing low-quality research
        db.add(
            CaseResearch(
                case_id=cid,
                source="example.com",
                title="Blog",
                summary="opinion",
                relevance="low",
                url="https://example.com/article",
            )
        )
        db.commit()

        # If research_case is called it will raise — ensure it's not called
        def fail_if_called(*args, **kwargs):
            raise AssertionError("research_case should not have been called")

        monkeypatch.setattr("app.api.cases.research_case", fail_if_called)

        resp = client.post(f"/cases/{cid}/synthesize?run_research=true")
        assert resp.status_code == 200
        assert resp.json()["case"]["status"] == "AWAITING_APPROVAL"

    finally:
        db.close()


def test_synthesize_run_research_handles_research_failure(monkeypatch):
    from app.db.database import SessionLocal
    from app.models.case import Case as CaseModel, CaseResearch, CaseStatus

    db = SessionLocal()

    try:
        create_response = client.post(
            "/cases",
            json={"title": "Research fails", "description": "fail"},
        )
        cid = create_response.json()["case"]["id"]

        # monkeypatch research_case to raise
        def bad_research(*args, **kwargs):
            raise ValueError("serpapi failure")

        monkeypatch.setattr("app.api.cases.research_case", bad_research)

        resp = client.post(f"/cases/{cid}/synthesize?run_research=true")
        assert resp.status_code == 400
        assert "serpapi failure" in resp.json()["detail"]

    finally:
        db.close()
