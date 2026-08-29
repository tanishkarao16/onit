from fastapi.testclient import TestClient
from app.main import app
from app.api import cases
import json

client = TestClient(app)


def test_parse_and_create_persists_evidence_pdf(monkeypatch):
    fake_response = {
        "output": {
            "elements": [
                {"role": "Text", "text": "Passenger: Alex Morgan\nBooking reference: ABC123", "confidence": 0.98, "page": 1},
                {"role": "Text", "text": "Airline: Example Airways", "confidence": 0.95, "page": 1},
            ]
        }
    }

    async def fake_parse_document(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(cases, "parse_document", fake_parse_document)

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
    cid = data["case"]["id"]
    assert cid is not None

    # verify evidence persisted
    from app.db.database import SessionLocal
    from app.models.case import CaseEvidence

    db = SessionLocal()
    try:
        evs = db.query(CaseEvidence).filter(CaseEvidence.case_id == cid).all()
        assert len(evs) == 1
        ev = evs[0]
        facts = json.loads(ev.extracted_facts or "{}")
        assert "passenger" in facts
        assert facts["passenger"]["value"] == "Alex Morgan"
        assert facts["passenger"]["provenance"]
    finally:
        db.close()


def test_parse_and_create_persists_text(monkeypatch):
    fake_response = {
        "output": {
            "elements": [
                {"role": "Text", "text": "Passenger: Sam Smith\nBooking reference: XYZ789"}
            ]
        }
    }

    async def fake_parse_document(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(cases, "parse_document", fake_parse_document)

    resp = client.post("/cases/parse-and-create", json={"text": "Passenger: Sam Smith\nBooking reference: XYZ789"})
    assert resp.status_code == 200
    data = resp.json()
    cid = data["case"]["id"]

    from app.db.database import SessionLocal
    from app.models.case import CaseEvidence

    db = SessionLocal()
    try:
        evs = db.query(CaseEvidence).filter(CaseEvidence.case_id == cid).all()
        assert len(evs) == 1
        facts = json.loads(evs[0].extracted_facts or "{}")
        assert facts["booking_reference"]["value"] == "XYZ789"
    finally:
        db.close()


def test_unsupported_file_type_rejected():
    with open("tests/fixtures/refund_case.pdf", "rb") as document:
        # simulate a zip by changing filename
        response = client.post(
            "/cases/parse-and-create",
            files={
                "file": (
                    "archive.zip",
                    document,
                    "application/zip",
                )
            },
        )

    assert response.status_code == 400


def test_partial_fields_missing(monkeypatch):
    fake_response = {"output": {"elements": [{"role": "Text", "text": "Some unrelated text only"}]}}

    async def fake_parse_document(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(cases, "parse_document", fake_parse_document)

    resp = client.post("/cases/parse-and-create", json={"text": "Some unrelated text only"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["case"]["passenger"] is None
    assert data["case"]["booking_reference"] is None


def test_provenance_in_extracted_facts(monkeypatch):
    fake_response = {
        "output": {
            "elements": [
                {"role": "Text", "text": "Passenger: Pat", "confidence": 0.9},
                {"role": "Text", "text": "Booking reference: QQQ111", "confidence": 0.8},
            ]
        }
    }

    async def fake_parse_document(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(cases, "parse_document", fake_parse_document)

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
    cid = response.json()["case"]["id"]

    from app.db.database import SessionLocal
    from app.models.case import CaseEvidence

    db = SessionLocal()
    try:
        ev = db.query(CaseEvidence).filter(CaseEvidence.case_id == cid).first()
        facts = json.loads(ev.extracted_facts or "{}")
        assert facts["booking_reference"]["provenance"]["confidence"] == 0.8
    finally:
        db.close()
