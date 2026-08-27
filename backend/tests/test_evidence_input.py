import json

from fastapi.testclient import TestClient

from app.main import app
from app.db.database import SessionLocal
from app.models.case import Case as CaseModel, CaseStatus, CaseEvidence


client = TestClient(app)


def test_text_evidence_extraction_and_case_update():
    db = SessionLocal()

    try:
        # create a minimal case
        resp = client.post("/cases", json={"title": "Evidence case", "description": "test"})
        cid = resp.json()["case"]["id"]

        # submit text evidence
        text = (
            "Passenger: Alex Morgan\n"
            "Airline: ANA\n"
            "Flight: NH123\n"
            "Booking reference: ABC123\n"
            "Flight cancellation date: August 1, 2026\n"
            "Amount paid: Y120,000\n"
            "Refund received: No\n"
        )

        r = client.post(f"/cases/{cid}/evidence", json={"text": text})
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        ev = data["evidence"]
        assert ev["case_id"] == cid
        facts = ev["extracted_facts"]
        assert facts["booking_reference"] == "ABC123"
        assert facts["airline"] == "ANA"
        assert facts["passenger"] == "Alex Morgan"

        # case should be updated where fields were empty
        db_case = db.get(CaseModel, cid)
        assert db_case.booking_reference == "ABC123"
        assert db_case.airline == "ANA"

    finally:
        db.close()


def test_upload_file_triggers_nutrient_and_persist(monkeypatch):
    db = SessionLocal()

    try:
        resp = client.post("/cases", json={"title": "File case", "description": "test"})
        cid = resp.json()["case"]["id"]

        # mock parse_document to return structured output
        async def fake_parse(path):
            return {"output": {"elements": [{"role": "Text", "text": "Passenger: Jane Doe\nBooking reference: XYZ789\nAirline: ExampleAir\nAmount paid: Y50,000"}]}}

        monkeypatch.setattr("app.api.cases.parse_document", fake_parse)

        # emulate upload by posting multipart with no actual file content
        files = {
            "file": ("doc.pdf", b"PDFBYTES", "application/pdf")
        }

        r = client.post(f"/cases/{cid}/evidence", files=files)
        assert r.status_code == 200
        ev = r.json()["evidence"]
        facts = ev["extracted_facts"]
        assert facts["booking_reference"] == "XYZ789"
        assert facts["passenger"] == "Jane Doe"

    finally:
        db.close()
