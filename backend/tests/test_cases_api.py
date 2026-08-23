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
    assert data["case"]["issue"] == (
        "Cancelled flight with refund not received"
    )
    assert data["case"]["recommended_action"] == (
        "Request the full refund from the airline"
    )
    assert data["case"]["priority"] == "high"
